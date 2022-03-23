import logging
import inspect
from collections import OrderedDict
import astroid
import re

from ._docstring_parser import DocstringParser
from ._typehint_parser import TypeHintParser
from ._base_node import NodeEntityBase, get_qualified_name
from ._argtype import ArgType


# Find types like ~azure.core.paging.ItemPaged and group returns ItemPaged.
# Regex is used to find shorten such instances in complex type
# for e,g, ~azure.core.ItemPaged.ItemPaged[~azure.communication.chat.ChatThreadInfo] to ItemPaged[ChatThreadInfo]
REGEX_FIND_LONG_TYPE = "((?:~?)[\w.]+\.+([\w]+))"


class FunctionNode(NodeEntityBase):
    """Function node class represents parsed function signature.
    Keyword args will be parsed and added to signature if docstring is available.
    :param str: namespace
    :param NodeEntityBase: parent_node
    :param function: obj
    :param bool: is_module_level
    """

    def __init__(self, namespace, parent_node, obj, is_module_level=False):
        super().__init__(namespace, parent_node, obj)
        self.annotations = []
        self.args = OrderedDict()
        self.return_type = None
        self.namespace_id = self.generate_id()
        # Set name space level ID as full name
        # Name space ID will be later updated for async methods
        self.full_name = self.namespace_id
        self.is_class_method = False
        self.is_module_level = is_module_level
        # Some of the methods wont be listed in API review
        # For e.g. ABC methods if class implements all ABC methods
        self.hidden = False
        self._inspect()


    def _inspect(self):
        logging.debug("Processing function {0}".format(self.name))
        try:
            code = inspect.getsource(self.obj).strip()
        except OSError:
            # skip functions with no source code
            self.is_async = False
            return
        
        for line in code.splitlines():
            # skip decorators
            if line.strip().startswith("@"):
                continue
            # the first non-decorator line should be the function signature
            self.is_async = line.strip().startswith("async def")
            self.def_key = "async def" if self.is_async else "def"
            break

        # Update namespace ID to reflect async status. Otherwise ID will conflict between sync and async methods
        if self.is_async:
            self.namespace_id += ":async"

        # Find decorators and any annotations
        node = astroid.extract_node(inspect.getsource(self.obj))
        if node.decorators:
            self.annotations = [
                "@{}".format(x.name)
                for x in node.decorators.nodes
                if hasattr(x, "name")
            ]
        self.is_class_method = "@classmethod" in self.annotations
        self._parse_function()


    def _parse_function(self):
        """
        Find positional and keyword arguements, type and default value and return type of method
        Parsing logic will follow below order to identify these information
        1. Identify args, types, default and ret type using inspect
        2. Parse type annotations if inspect doesn't have complete info
        3. Parse docstring to find keyword arguements
        4. Parse type hints
        """
        # Add cls as first arg for class methods in API review tool
        if "@classmethod" in self.annotations:
            self.args["cls"] = ArgType(name="cls", argtype=None, default=inspect.Parameter.empty, keyword=None)

        # Find signature to find positional args and return type
        sig = inspect.signature(self.obj)
        params = sig.parameters
        # Add all keyword only args here temporarily until docstring is parsed
        # This is to handle the scenario for keyword arg typehint (py3 style is present in signature itself)
        self.kw_args = OrderedDict()
        for argname, argvalues in params.items():
            kind = argvalues.kind
            keyword = "keyword" if kind == inspect.Parameter.KEYWORD_ONLY else None
            arg = ArgType(name=argname, argtype=get_qualified_name(argvalues.annotation, self.namespace), default=argvalues.default, func_node=self, keyword=keyword)

            # Store handle to kwarg object to replace it later
            if kind == inspect.Parameter.VAR_KEYWORD:
                arg.argname = f"**{argname}"

            if kind == inspect.Parameter.KEYWORD_ONLY:
                self.kw_args[arg.argname] = arg
            elif kind == inspect.Parameter.VAR_POSITIONAL:
                # to work with docstring parsing, the key must
                # not have the * in it.
                arg.argname = f"*{argname}"
                self.args[argname] = arg
            else:
                self.args[arg.argname] = arg

        if sig.return_annotation:
            self.return_type = get_qualified_name(sig.return_annotation, self.namespace)

        self._parse_docstring()
        self._parse_typehint()
        self._order_final_args()


    def _order_final_args(self):
        # find and temporarily remove the kwargs param from arguments
        #  if present from the signature inspection
        kwargs_param = None
        kwargs_name = None
        if not kwargs_param:
            for argname in self.args:
                # find kwarg params with a different name, like config
                if argname.startswith("**"):
                    kwargs_name = argname
                    break
            if kwargs_name:
                kwargs_param = self.args.pop(kwargs_name, None)

        # add keyword args
        if self.kw_args:
            # Add separator to differentiate pos_arg and keyword args
            self.args["*"] = ArgType("*", default=inspect.Parameter.empty, argtype=None, keyword=None)
            for argname, arg in sorted(self.kw_args.items()):
                arg.function_node = self
                self.args[argname] = arg

        # re-append "**kwargs" to the end of the arguments list
        if kwargs_param:
            self.args[kwargs_name] = kwargs_param

    def _parse_docstring(self):
        # Parse docstring to get list of keyword args, type and default value for both positional and
        # kw args and return type( if not already found in signature)
        docstring = ""
        if hasattr(self.obj, "__doc__"):
            docstring = getattr(self.obj, "__doc__")
        # Refer docstring at class if this is constructor and docstring is missing for __init__
        if (
            not docstring
            and self.name == "__init__"
            and hasattr(self.parent_node.obj, "__doc__")
        ):
            docstring = getattr(self.parent_node.obj, "__doc__")

        if docstring:
            #  Parse doc string to find missing types, kwargs and return type
            parsed_docstring = DocstringParser(docstring)

            # Set return type if not already set
            if not self.return_type and parsed_docstring.ret_type:
                logging.debug(
                    "Setting return type from docstring for method {}".format(self.name)
                )
                self.return_type = parsed_docstring.ret_type

            # Update positional argument metadata from the docstring; otherwise, stick with
            # what was parsed from the signature.
            for argname, signature_arg in self.args.items():
                docstring_match = parsed_docstring.pos_args.get(argname, None)
                if not docstring_match:
                    continue
                signature_arg.argtype = docstring_match.argtype or signature_arg.argtype
                signature_arg.default = docstring_match.default or signature_arg.default

            # Update keyword argument metadata from the docstring; otherwise, stick with
            # what was parsed from the signature.
            remaining_docstring_kwargs = set(parsed_docstring.kw_args.keys())
            for argname, kw_arg in self.kw_args.items():
                docstring_match = parsed_docstring.kw_args.get(argname, None)
                if not docstring_match:
                    continue
                remaining_docstring_kwargs.remove(argname)
                if not kw_arg.is_required:
                    kw_arg.argtype = kw_arg.argtype or docstring_match.argtype 
                    kw_arg.default = kw_arg.default or docstring_match.default
            
            # ensure any kwargs described only in the docstrings are added
            for argname in remaining_docstring_kwargs:
                self.kw_args[argname] = parsed_docstring.kw_args[argname]


    def _generate_short_type(self, long_type):
        short_type = long_type
        groups = re.findall(REGEX_FIND_LONG_TYPE, short_type)
        for g in groups:
            short_type = short_type.replace(g[0], g[1])
        return short_type


    def _parse_typehint(self):

        # Skip parsing typehint if typehint is not expected for async methods
        # and if return type is already found
        if self.return_type and self.is_async:
            return

        # Parse type hint to get return type and types for positional args
        typehint_parser = TypeHintParser(self.obj)
        # Find return type from type hint if return type is not already set
        type_hint_ret_type = typehint_parser.ret_type
        # Type hint must be present for all APIs. Flag it as an error if typehint is missing
        if  not type_hint_ret_type:
            return

        # because the typehint isn't subject to the 2-line limit, prefer it over
        # a type parsed from the docstring.
        self.return_type = type_hint_ret_type or self.return_type


    def _generate_signature_token(self, apiview):
        apiview.add_punctuation("(")
        args_count = len(self.args)
        use_multi_line = args_count > 2
        # Show args in individual line if method has more than 4 args and use two tabs to properly aign them
        if use_multi_line:
            apiview.begin_group()
            apiview.begin_group()

        # Generate token for each arg
        for index, key in enumerate(self.args.keys()):
            # Add new line if args are listed in new line
            if use_multi_line:
                apiview.add_newline()
                apiview.add_whitespace()

            self.args[key].generate_tokens(
                apiview, self.namespace_id, use_multi_line
            )
            # Add punctuation between types except for last one
            if index < args_count - 1:
                apiview.add_punctuation(",", False, True)

        if use_multi_line:
            apiview.add_newline()
            apiview.end_group()
            apiview.add_whitespace()
            apiview.add_punctuation(")")
            apiview.end_group()
        else:
            apiview.add_punctuation(")")


    def generate_tokens(self, apiview):
        """Generates token for function signature
        :param ApiView: apiview
        """
        logging.info("Processing method {0} in class {1}".format(self.name, self.parent_node.namespace_id))
        # Add tokens for annotations
        for annot in self.annotations:
            apiview.add_whitespace()
            apiview.add_keyword(annot)
            apiview.add_newline()

        apiview.add_whitespace()
        apiview.add_line_marker(self.namespace_id)
        if self.is_async:
            apiview.add_keyword("async", False, True)

        apiview.add_keyword("def", False, True)
        # Show fully qualified name for module level function and short name for instance functions
        apiview.add_text(
            self.namespace_id, self.full_name if self.is_module_level else self.name,
            add_cross_language_id=True
        )
        # Add parameters
        self._generate_signature_token(apiview)
        if self.return_type:
            apiview.add_punctuation("->", True, True)
            # Add line marker id if signature is displayed in multi lines
            if len(self.args) > 2:
                line_id = "{}.returntype".format(self.namespace_id)
                apiview.add_line_marker(line_id)
            apiview.add_type(self.return_type)
        apiview.add_newline()

        for err in self.pylint_errors:
            err.generate_tokens(apiview, self.namespace_id)        

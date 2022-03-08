import inspect
from ._base_node import NodeEntityBase


class VariableNode(NodeEntityBase):
    """Variable node represents class and instance variable defined in a class
    """

    def __init__(self, *, namespace, parent_node, name, type_name, value, is_ivar, dataclass_properties=None):
        super().__init__(namespace, parent_node, type_name)
        self.name = name
        self.type = type_name
        self.is_ivar = is_ivar
        self.namespace_id = "{0}.{1}({2})".format(
            self.parent_node.namespace_id, self.name, self.type
        )
        self.value = value
        self.dataclass_properties = dataclass_properties

    def generate_tokens(self, apiview):
        """Generates token for the node
        :param ApiView: apiview
        """
        apiview.add_keyword("ivar" if self.is_ivar else "cvar", False, True)
        apiview.add_line_marker(self.namespace_id)
        apiview.add_text(self.namespace_id, self.name)
        # Add type
        if self.type:
            apiview.add_punctuation(":", False, True)
            apiview.add_type(self.type)

        if self.value and not self.dataclass_properties:
            apiview.add_punctuation("=", True, True)
            add_value = (
                apiview.add_stringliteral
                if self.type == "str"
                else apiview.add_literal
            )
            add_value(self.value)
        
        if self.dataclass_properties:
            apiview.add_punctuation("=", True, True)
            apiview.add_text(None, "field")
            apiview.add_punctuation("(")
            properties = self.dataclass_properties
            for (i, (name, value)) in enumerate(properties):
                apiview.add_text(self.namespace_id, name)
                apiview.add_punctuation("=")
                apiview.add_text(None, str(value))
                if i < len(properties) - 1:
                    apiview.add_punctuation(",", postfix_space=True)
            apiview.add_punctuation(")")                

    def print_errors(self):
        if self.errors:
            print("{0}: {1}".format("ivar" if self.is_ivar else "cvar", self.name))
            for e in self.errors:
                print("    {}".format(e))
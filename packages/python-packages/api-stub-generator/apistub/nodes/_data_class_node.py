from dataclasses import dataclass, _MISSING_TYPE
import logging
import inspect
from enum import Enum
import operator

from ._base_node import get_qualified_name
from ._class_node import ClassNode
from ._variable_node import VariableNode


class DataClassNode(ClassNode):
    """Class node to represent parsed data classes
    """

    def __init__(self, *, name, namespace, parent_node, obj, pkg_root_namespace):
        super().__init__(name=name, namespace=namespace, parent_node=parent_node, obj=obj, pkg_root_namespace=pkg_root_namespace)
        self.dataclass_fields = getattr(obj, "__dataclass_fields__", [])
        self.dataclass_params = getattr(obj, "__dataclass_params__", None)
        self._handle_dataclass()

    def _handle_dataclass(self):
        # while dataclass properties looks like class variables, they are
        # actually instance variables
        for (name, properties) in self.dataclass_fields.items():
            # convert the cvar to ivar
            var_match = [v for v in self.child_nodes if isinstance(v, VariableNode) and v.name == name]
            if var_match:
                match = var_match[0]
                match.is_ivar = True
                match.dataclass_properties = self._extract_properties(properties)

    def _extract_properties(self, params):
        all_props = inspect.getmembers(params)
        props = []
        for prop in all_props:
            if not prop[0].startswith("_"):
                name = prop[0]
                value = prop[1]
                props.append((name, value))
        return props

    def _generate_dataclass_property_tokens(self, apiview):
        if self.dataclass_params:
            apiview.add_punctuation("(")
            properties = self._extract_properties(self.dataclass_params)
            for (i, (name, value)) in enumerate(properties):
                apiview.add_text(self.namespace_id, name)
                apiview.add_punctuation("=")
                apiview.add_text(None, str(value))
                if i != len(properties) - 1:
                    apiview.add_punctuation(",", postfix_space=True)
            apiview.add_punctuation(")")                

    def generate_tokens(self, apiview):
        """Generates token for the node and it's children recursively and add it to apiview
        :param ApiView: apiview
        """
        logging.info("Processing class {}".format(self.parent_node.namespace_id))
        # Generate class name line
        apiview.add_whitespace()
        apiview.add_text(self.namespace_id, "@dataclass")
        self._generate_dataclass_property_tokens(apiview)
        apiview.add_newline()
        super().generate_tokens(apiview)

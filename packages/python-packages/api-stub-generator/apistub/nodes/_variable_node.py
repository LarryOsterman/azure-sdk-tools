from ._base_node import NodeEntityBase


class VariableNode(NodeEntityBase):
    """Variable node represents class and instance variable defined in a class
    """

    def __init__(self, *, namespace, parent_node, name, type_name, value, is_ivar):
        super().__init__(namespace, parent_node, type_name)
        self.name = name
        self.type = type_name
        self.is_ivar = is_ivar
        self.namespace_id = "{0}.{1}({2})".format(
            self.parent_node.namespace_id, self.name, self.type
        )
        self.value = value

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

        if self.value:
            apiview.add_punctuation("=", True, True)
            add_value = (
                apiview.add_stringliteral
                if self.type == "str"
                else apiview.add_literal
            )
            add_value(self.value)
        for err in self.pylint_errors:
            err.generate_tokens(apiview, self.namespace_id)

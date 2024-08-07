using APIView.TreeToken;
using APIView;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace APIViewWeb.LeanModels
{

    public class CodePanelRawData
    {
        public IEnumerable<CommentItemModel> Comments { get; set; } = new List<CommentItemModel>();
        public List<APITreeNode> APIForest { get; set; } = new List<APITreeNode>();
        public CodeDiagnostic[] Diagnostics { get; set; } = new CodeDiagnostic[0];
        public string Language { get; set; }
        public bool ApplySkipDiff { get; set; }
        public bool SkipDocsWhenDiffing { get; set; }
    }

    public class CodePanelRowData
    {
        public CodePanelRowDatatype Type { get; set; }
        public int? LineNumber { get; set; }
        [JsonIgnore]
        public List<StructuredToken> RowOfTokensObj { get; set; } = new List<StructuredToken>();
        public List<StructuredToken> RowOfTokens => RowOfTokensObj.Count > 0 ? RowOfTokensObj : null;
        public string NodeId { get; set; }
        public string NodeIdHashed { get; set; }
        public int RowPositionInGroup { get; set; } // The position / index of the row within the group of similar rows
        public int AssociatedRowPositionInGroup { get; set; } // For comment threads, this is the position of the associated code line within the group of similar rows
        public RowOfTokensPosition RowOfTokensPosition { get; set; }
        [JsonIgnore]
        public HashSet<string> RowClassesObj { get; set; } = new HashSet<string>();
        public HashSet<string> RowClasses => RowClassesObj.Count > 0 ? RowClassesObj : null;
        public int? Indent { get; set; }
        public DiffKind DiffKind { get; set; }
        public string ToggleDocumentationClasses { get; set; }
        public string ToggleCommentsClasses { get; set; }
        public CodeDiagnostic Diagnostics { get; set; }
        [JsonIgnore]
        public List<CommentItemModel> CommentsObj { get; set; } = new List<CommentItemModel>();
        public List<CommentItemModel> Comments => CommentsObj.Count > 0 ? CommentsObj : null;
        public bool IsResolvedCommentThread { get; set; }
        public bool IsHiddenAPI { get; set; }

    }

    public class CodePanelNodeMetaData
    {
        [JsonIgnore]
        public List<CodePanelRowData> DocumentationObj { get; set; } = new List<CodePanelRowData>();
        public List<CodePanelRowData> Documentation => DocumentationObj.Count > 0 ? DocumentationObj : null;
        [JsonIgnore]
        public List<CodePanelRowData> DiagnosticsObj { get; set; } = new List<CodePanelRowData>();
        public List<CodePanelRowData> Diagnostics => DiagnosticsObj.Count > 0 ? DiagnosticsObj : null;
        [JsonIgnore]
        public List<CodePanelRowData> CodeLinesObj { get; set; } = new List<CodePanelRowData>();
        public List<CodePanelRowData> CodeLines => CodeLinesObj.Count > 0 ? CodeLinesObj : null;
        [JsonIgnore]
        public ConcurrentDictionary<int, CodePanelRowData> CommentThreadObj { get; set; } = new ConcurrentDictionary<int, CodePanelRowData>(); //Dictionary key map to the index of the code line within this node which the comment thread is mapped to
        public ConcurrentDictionary<int, CodePanelRowData> CommentThread => CommentThreadObj.Count > 0 ? CommentThreadObj : null;
        public NavigationTreeNode NavigationTreeNode { get; set; }
        public string ParentNodeIdHashed { get; set; }
        [JsonIgnore]
        public ConcurrentDictionary<int, string> ChildrenNodeIdsInOrderObj { get; set; } = new ConcurrentDictionary<int, string>();
        public ConcurrentDictionary<int, string> ChildrenNodeIdsInOrder => ChildrenNodeIdsInOrderObj.Count > 0 ? ChildrenNodeIdsInOrderObj : null;
        public bool IsNodeWithDiff { get; set; }
        public bool IsNodeWithDiffInDescendants { get; set; }
        public bool IsNodeWithNoneDocDiffInDescendants { get; set; }
        public string BottomTokenNodeIdHash { get; set; }
    }

    public class CodePanelData
    {
        [JsonIgnore]
        public ConcurrentDictionary<string, CodePanelNodeMetaData> NodeMetaDataObj { get; set; } = new ConcurrentDictionary<string, CodePanelNodeMetaData>();
        public ConcurrentDictionary<string, CodePanelNodeMetaData> NodeMetaData => NodeMetaDataObj.Count > 0 ? NodeMetaDataObj : null;
        public bool HasDiff { get; set; } = false;
    }
}

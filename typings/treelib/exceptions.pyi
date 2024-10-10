class NodePropertyError(Exception): ...
class NodeIDAbsentError(NodePropertyError): ...
class NodePropertyAbsentError(NodePropertyError): ...
class MultipleRootError(Exception): ...
class DuplicatedNodeIdError(Exception): ...
class LinkPastRootNodeError(Exception): ...
class InvalidLevelNumber(Exception): ...
class LoopError(Exception): ...

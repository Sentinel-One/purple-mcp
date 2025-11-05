"""Pydantic models for misconfigurations data structures."""

from enum import Enum

from pydantic import BaseModel, Field

# Enums


class MisconfigurationSeverity(str, Enum):
    """Misconfiguration severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"
    UNKNOWN = "UNKNOWN"


class Status(str, Enum):
    """Misconfiguration status values."""

    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    RESOLVED = "RESOLVED"
    RISK_ACKED = "RISK_ACKED"
    SUPPRESSED = "SUPPRESSED"
    TO_BE_PATCHED = "TO_BE_PATCHED"


class AnalystVerdict(str, Enum):
    """Analyst verdict for misconfigurations."""

    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class ViewType(str, Enum):
    """View type for misconfiguration queries."""

    ALL = "ALL"
    CLOUD = "CLOUD"
    KUBERNETES = "KUBERNETES"
    IDENTITY = "IDENTITY"
    INFRASTRUCTURE_AS_CODE = "INFRASTRUCTURE_AS_CODE"
    ADMISSION_CONTROLLER = "ADMISSION_CONTROLLER"
    OFFENSIVE_SECURITY = "OFFENSIVE_SECURITY"
    SECRET_SCANNING = "SECRET_SCANNING"


class EnforcementAction(str, Enum):
    """Enforcement action type."""

    DETECT = "DETECT"
    DETECT_AND_PROTECT = "DETECT_AND_PROTECT"


class AssetCriticality(str, Enum):
    """Asset criticality levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class OsType(str, Enum):
    """Operating system types."""

    AIX = "AIX"
    ANDROID = "ANDROID"
    APPLE = "APPLE"
    CISCO = "CISCO"
    HP_UX = "HP_UX"
    IOS = "IOS"
    IPADOS = "IPADOS"
    LINUX = "LINUX"
    MACOS = "MACOS"
    SOLARIS = "SOLARIS"
    UNKNOWN = "UNKNOWN"
    UNRECOGNIZED = "UNRECOGNIZED"
    WINDOWS = "WINDOWS"
    WYSE = "WYSE"


class HistoryEventType(str, Enum):
    """History event types."""

    CREATION = "CREATION"
    STATUS = "STATUS"
    ANALYST_VERDICT = "ANALYST_VERDICT"
    USER_ASSIGNMENT = "USER_ASSIGNMENT"
    NOTES = "NOTES"
    WORKFLOW_ACTION = "WORKFLOW_ACTION"


class ComplianceStatus(str, Enum):
    """Compliance status values."""

    FAIL = "FAIL"
    FAILURE = "FAILURE"
    SUCCESS = "SUCCESS"
    OTHER = "OTHER"


class AssetScopeLevel(str, Enum):
    """Asset scope levels."""

    account = "account"
    group = "group"
    site = "site"


# Filter Input Types


class EqualFilterBooleanInput(BaseModel):
    """Strictly matching a boolean value."""

    value: bool | None = None


class EqualFilterIntegerInput(BaseModel):
    """Strictly matching an integer value."""

    value: int | None = None


class EqualFilterLongInput(BaseModel):
    """Strictly matching a long value."""

    value: int | None = None


class EqualFilterStringInput(BaseModel):
    """Strictly matching a string value."""

    value: str | None = None


class InFilterBooleanInput(BaseModel):
    """Filter for multiple boolean values."""

    values: list[bool | None] = Field(default_factory=list)


class InFilterIntegerInput(BaseModel):
    """Filter for multiple integer values."""

    values: list[int] = Field(default_factory=list)


class InFilterLongInput(BaseModel):
    """Filter for multiple long values."""

    values: list[int] = Field(default_factory=list)


class InFilterStringInput(BaseModel):
    """Filter for multiple string values."""

    values: list[str] = Field(default_factory=list)


class RangeFilterIntegerInput(BaseModel):
    """Filter for ranges of integer types."""

    start: int | None = None
    start_inclusive: bool = Field(default=True, alias="startInclusive")
    end: int | None = None
    end_inclusive: bool = Field(default=True, alias="endInclusive")


class RangeFilterLongInput(BaseModel):
    """Filter for ranges of long types."""

    start: int | None = None
    start_inclusive: bool = Field(default=True, alias="startInclusive")
    end: int | None = None
    end_inclusive: bool = Field(default=True, alias="endInclusive")


class FulltextFilterInput(BaseModel):
    """Filter for full-text search."""

    values: list[str] = Field(default_factory=list)


class FulltextInFilterInput(BaseModel):
    """Filter for multi-value full-text search."""

    values: list[str] = Field(default_factory=list)


class FilterInput(BaseModel):
    """Filter for a field - only one filter type can be defined."""

    field_id: str = Field(alias="fieldId")
    is_negated: bool = Field(default=False, alias="isNegated")

    # Filter type options (only one should be set)
    boolean_equal: EqualFilterBooleanInput | None = Field(None, alias="booleanEqual")
    boolean_in: InFilterBooleanInput | None = Field(None, alias="booleanIn")
    int_equal: EqualFilterIntegerInput | None = Field(None, alias="intEqual")
    int_in: InFilterIntegerInput | None = Field(None, alias="intIn")
    int_range: RangeFilterIntegerInput | None = Field(None, alias="intRange")
    long_equal: EqualFilterLongInput | None = Field(None, alias="longEqual")
    long_in: InFilterLongInput | None = Field(None, alias="longIn")
    long_range: RangeFilterLongInput | None = Field(None, alias="longRange")
    string_equal: EqualFilterStringInput | None = Field(None, alias="stringEqual")
    string_in: InFilterStringInput | None = Field(None, alias="stringIn")
    match: FulltextFilterInput | None = None
    match_in: FulltextInFilterInput | None = Field(None, alias="matchIn")
    date_time_range: RangeFilterLongInput | None = Field(None, alias="dateTimeRange")


class AndFilterSelectionInput(BaseModel):
    """List of filters with implicit AND between them."""

    and_filters: list[FilterInput] = Field(default_factory=list, alias="and")


class OrFilterSelectionInput(BaseModel):
    """List of AndFilterSelection with implicit OR between them."""

    or_filters: list[AndFilterSelectionInput] = Field(default_factory=list, alias="or")


# Core Entity Models


class User(BaseModel):
    """User information.

    All fields are optional to support partial fragment queries where only specific
    fields are requested (e.g., assignee { email }).
    """

    id: str | None = None
    email: str | None = None
    full_name: str | None = Field(default=None, alias="fullName")
    deleted: bool = False


class Account(BaseModel):
    """Account information."""

    id: str | None = None
    name: str | None = None


class Site(BaseModel):
    """Site information."""

    id: str | None = None
    name: str | None = None


class Group(BaseModel):
    """Group information."""

    id: str | None = None
    name: str | None = None


class Scope(BaseModel):
    """Scope information with account/site/group hierarchy."""

    account: Account | None = None
    site: Site | None = None
    group: Group | None = None


class CloudInfo(BaseModel):
    """Asset's cloud information."""

    account_id: str | None = Field(None, alias="accountId")
    account_name: str | None = Field(None, alias="accountName")
    provider_name: str | None = Field(None, alias="providerName")
    region: str | None = None
    resource_id: str | None = Field(None, alias="resourceId")
    resource_link: str | None = Field(None, alias="resourceLink")


class KubernetesInfo(BaseModel):
    """Asset's Kubernetes information."""

    cluster: str | None = None
    cluster_id: str | None = Field(None, alias="clusterId")
    namespace: str | None = None


class Asset(BaseModel):
    """Asset basic information."""

    id: str
    external_id: str | None = Field(None, alias="externalId")
    name: str | None = None
    type: str | None = None
    category: str | None = None
    subcategory: str | None = None
    domain: str | None = None
    agent_uuid: str | None = Field(None, alias="agentUuid")
    privileged: bool | None = None
    criticality: AssetCriticality | None = None
    os_type: OsType | None = Field(None, alias="osType")
    cloud_info: CloudInfo | None = Field(None, alias="cloudInfo")
    kubernetes_info: KubernetesInfo | None = Field(None, alias="kubernetesInfo")


class Policy(BaseModel):
    """Policy basic information."""

    id: str | None = None
    version: str | None = None
    group: str | None = None


class PolicyDetail(BaseModel):
    """Policy details."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    version: str | None = None
    group: str | None = None


class Cnapp(BaseModel):
    """CNAPP basic information."""

    policy: Policy | None = None
    verified_exploitable: bool | None = Field(None, alias="verifiedExploitable")


class CnappDetail(BaseModel):
    """CNAPP details."""

    policy: PolicyDetail | None = None
    verified_exploitable: bool | None = Field(None, alias="verifiedExploitable")
    auto_remediation: bool | None = Field(None, alias="autoRemediation")
    ha_connection_id: str | None = Field(None, alias="haConnectionId")
    ha_template_id: str | None = Field(None, alias="haTemplateId")


class Secret(BaseModel):
    """Secret details."""

    type: str | None = None
    hash: str | None = None
    valid: bool | None = None


class Evidence(BaseModel):
    """Evidence details."""

    file_name: str | None = Field(None, alias="fileName")
    file_type: str | None = Field(None, alias="fileType")
    file_url: str | None = Field(None, alias="fileUrl")
    iac_framework: str | None = Field(None, alias="iacFramework")
    ip_address: str | None = Field(None, alias="ipAddress")
    port: int | None = None
    subdomain: str | None = None
    commited_by: str | None = Field(None, alias="commitedBy")
    secret: Secret | None = None


class AdmissionRequest(BaseModel):
    """Admission request basic information."""

    category: str | None = None
    resource_name: str | None = Field(None, alias="resourceName")
    resource_namespace: str | None = Field(None, alias="resourceNamespace")
    resource_type: str | None = Field(None, alias="resourceType")
    user_name: str | None = Field(None, alias="userName")
    user_uid: str | None = Field(None, alias="userUid")
    user_group: str | None = Field(None, alias="userGroup")


class AdmissionRequestDetail(BaseModel):
    """Admission request details."""

    category: str | None = None
    resource_name: str | None = Field(None, alias="resourceName")
    resource_namespace: str | None = Field(None, alias="resourceNamespace")
    resource_type: str | None = Field(None, alias="resourceType")
    user_name: str | None = Field(None, alias="userName")
    user_uid: str | None = Field(None, alias="userUid")
    user_group: str | None = Field(None, alias="userGroup")


class MitreAttack(BaseModel):
    """MITRE ATT&CK identification.

    All fields are optional to support partial fragment queries where only specific
    fields are requested. Note that techniqueId should always be included in practice
    as it's the primary identifier.
    """

    technique_id: str | None = Field(None, alias="techniqueId")
    technique_name: str | None = Field(None, alias="techniqueName")
    technique_url: str | None = Field(None, alias="techniqueUrl")
    tactic_name: str | None = Field(None, alias="tacticName")
    tactic_uid: str | None = Field(None, alias="tacticUid")


class KbArticle(BaseModel):
    """Knowledge base article reference."""

    title: str
    url: str


class Compliance(BaseModel):
    """Compliance details."""

    standards: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    compliance_standards: list[KbArticle] = Field(
        default_factory=list, alias="complianceStandards"
    )
    compliance_references: list[KbArticle] = Field(
        default_factory=list, alias="complianceReferences"
    )
    status: ComplianceStatus | None = None


class Remediation(BaseModel):
    """Remediation details."""

    mitigable: bool | None = None
    mitigation_steps: str | None = Field(None, alias="mitigationSteps")
    references: list[KbArticle] = Field(default_factory=list)


class FailedRule(BaseModel):
    """Failed rule details."""

    name: str | None = None
    description: str | None = None
    severity: MisconfigurationSeverity | None = None
    impact: str | None = None
    compliance: list[str] | None = None
    recommended_action: str | None = Field(None, alias="recommendedAction")
    enforcement_settings: EnforcementAction | None = Field(None, alias="enforcementSettings")


class FindingDataProperty(BaseModel):
    """Finding data property."""

    name: str | None = None
    value: str | None = None


class FindingData(BaseModel):
    """Finding data."""

    properties: list[FindingDataProperty] = Field(default_factory=list)
    exposure_reason: str | None = Field(None, alias="exposureReason")
    context: dict[str, object] | None = None  # JSON type


class Misconfiguration(BaseModel):
    """Main misconfiguration model.

    All fields except 'id' are optional to support dynamic field selection.
    When using custom field selection, only requested fields will be populated.
    """

    id: str
    external_id: str | None = Field(None, alias="externalId")
    name: str | None = None
    severity: MisconfigurationSeverity | None = None
    status: Status | None = None
    asset: Asset | None = None
    scope: Scope | None = None
    product: str | None = None
    vendor: str | None = None
    detected_at: str | None = Field(None, alias="detectedAt")
    event_time: str | None = Field(None, alias="eventTime")
    environment: str | None = None

    # Optional fields
    analyst_verdict: AnalystVerdict | None = Field(None, alias="analystVerdict")
    assignee: User | None = None
    cnapp: Cnapp | None = None
    compliance_standards: list[str] | None = Field(None, alias="complianceStandards")
    data_classification_categories: list[str] | None = Field(
        None, alias="dataClassificationCategories"
    )
    data_classification_data_types: list[str] | None = Field(
        None, alias="dataClassificationDataTypes"
    )
    enforcement_action: EnforcementAction | None = Field(None, alias="enforcementAction")
    evidence: Evidence | None = None
    exclusion_policy_id: str | None = Field(None, alias="exclusionPolicyId")
    exploit_id: str | None = Field(None, alias="exploitId")
    exposure_reason: str | None = Field(None, alias="exposureReason")
    last_seen_at: str | None = Field(None, alias="lastSeenAt")
    mitigable: bool | None = None
    misconfiguration_type: str | None = Field(None, alias="misconfigurationType")
    mitre_attacks: list[MitreAttack] = Field(default_factory=list, alias="mitreAttacks")
    organization: str | None = None
    remediation: Remediation | None = None
    resource_uid: str | None = Field(None, alias="resourceUid")
    admission_request: AdmissionRequest | None = Field(None, alias="admissionRequest")


class MisconfigurationDetail(BaseModel):
    """Misconfiguration detail model with full information."""

    id: str
    external_id: str = Field(alias="externalId")
    name: str
    description: str | None = None
    severity: MisconfigurationSeverity
    status: Status
    asset: Asset
    scope: Scope
    scope_level: AssetScopeLevel = Field(alias="scopeLevel")
    product: str
    vendor: str
    detected_at: str = Field(alias="detectedAt")
    event_time: str = Field(alias="eventTime")
    environment: str
    compliance: Compliance
    remediation: Remediation
    failed_rules: list[FailedRule] = Field(default_factory=list, alias="failedRules")
    finding_data: FindingData = Field(alias="findingData")
    mitre_attacks: list[MitreAttack] = Field(default_factory=list, alias="mitreAttacks")

    # Optional fields
    analyst_verdict: AnalystVerdict | None = Field(None, alias="analystVerdict")
    assignee: User | None = None
    cnapp: CnappDetail | None = None
    data_classification_categories: list[str] | None = Field(
        None, alias="dataClassificationCategories"
    )
    data_classification_data_types: list[str] | None = Field(
        None, alias="dataClassificationDataTypes"
    )
    enforcement_action: EnforcementAction | None = Field(None, alias="enforcementAction")
    evidence: Evidence | None = None
    exclusion_policy_id: str | None = Field(None, alias="exclusionPolicyId")
    exploit_id: str | None = Field(None, alias="exploitId")
    exposure_id: str | None = Field(None, alias="exposureId")
    last_seen_at: str | None = Field(None, alias="lastSeenAt")
    misconfiguration_type: str | None = Field(None, alias="misconfigurationType")
    organization: str | None = None
    resource_uid: str | None = Field(None, alias="resourceUid")
    self_link: str | None = Field(None, alias="selfLink")
    admission_request: AdmissionRequestDetail | None = Field(None, alias="admissionRequest")


class PageInfo(BaseModel):
    """Pagination information."""

    has_next_page: bool = Field(alias="hasNextPage")
    has_previous_page: bool = Field(alias="hasPreviousPage")
    start_cursor: str | None = Field(None, alias="startCursor")
    end_cursor: str | None = Field(None, alias="endCursor")


class MisconfigurationEdge(BaseModel):
    """Misconfiguration edge in a connection."""

    node: Misconfiguration
    cursor: str


class MisconfigurationConnection(BaseModel):
    """Misconfiguration connection for pagination."""

    edges: list[MisconfigurationEdge] = Field(default_factory=list)
    page_info: PageInfo = Field(alias="pageInfo")
    total_count: int | None = Field(None, alias="totalCount")


class MisconfigurationNote(BaseModel):
    """Misconfiguration note model."""

    id: str
    misconfiguration_id: str = Field(alias="misconfigurationId")
    text: str
    author: User
    created_at: str = Field(alias="createdAt")
    updated_at: str | None = Field(None, alias="updatedAt")


class MisconfigurationNoteEdge(BaseModel):
    """Misconfiguration note edge in a connection."""

    node: MisconfigurationNote
    cursor: str


class MisconfigurationNoteConnection(BaseModel):
    """Misconfiguration note connection for pagination."""

    edges: list[MisconfigurationNoteEdge] = Field(default_factory=list)
    page_info: PageInfo = Field(alias="pageInfo")
    total_count: int | None = Field(None, alias="totalCount")


class MisconfigurationHistoryItem(BaseModel):
    """Misconfiguration history item."""

    event_type: HistoryEventType = Field(alias="eventType")
    event_text: str = Field(alias="eventText")
    created_at: str = Field(alias="createdAt")


class MisconfigurationHistoryItemEdge(BaseModel):
    """Misconfiguration history item edge in a connection."""

    node: MisconfigurationHistoryItem
    cursor: str


class MisconfigurationHistoryItemConnection(BaseModel):
    """Misconfiguration history item connection for pagination."""

    edges: list[MisconfigurationHistoryItemEdge] = Field(default_factory=list)
    page_info: PageInfo = Field(alias="pageInfo")
    total_count: int | None = Field(None, alias="totalCount")


# Response wrapper models for consistency


class GetMisconfigurationResponse(BaseModel):
    """Response wrapper for get_misconfiguration query."""

    misconfiguration: MisconfigurationDetail


class ListMisconfigurationsResponse(BaseModel):
    """Response wrapper for list_misconfigurations query."""

    misconfigurations: MisconfigurationConnection


class SearchMisconfigurationsResponse(BaseModel):
    """Response wrapper for search_misconfigurations query."""

    misconfigurations: MisconfigurationConnection


class GetMisconfigurationNotesResponse(BaseModel):
    """Response wrapper for get_misconfiguration_notes query."""

    misconfiguration_notes: MisconfigurationNoteConnection = Field(alias="misconfigurationNotes")


class GetMisconfigurationHistoryResponse(BaseModel):
    """Response wrapper for get_misconfiguration_history query."""

    misconfiguration_history: MisconfigurationHistoryItemConnection = Field(
        alias="misconfigurationHistory"
    )

"""Pydantic models for vulnerabilities data structures."""

from enum import Enum

from pydantic import BaseModel, Field

# Enums


class VulnerabilitySeverity(str, Enum):
    """Vulnerability severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class Status(str, Enum):
    """Vulnerability status values."""

    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    RESOLVED = "RESOLVED"
    RISK_ACKED = "RISK_ACKED"
    SUPPRESSED = "SUPPRESSED"
    TO_BE_PATCHED = "TO_BE_PATCHED"


class AnalystVerdict(str, Enum):
    """Analyst verdict for vulnerabilities."""

    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"


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


class SoftwareType(str, Enum):
    """Software types."""

    APP = "APP"
    OS = "OS"


class ExploitMaturity(str, Enum):
    """Exploit code maturity levels."""

    FUNCTIONAL = "FUNCTIONAL"
    HIGH = "HIGH"
    MATURITY_NOT_DEFINED = "MATURITY_NOT_DEFINED"
    PROOF_OF_CONCEPT = "PROOF_OF_CONCEPT"
    UNPROVEN = "UNPROVEN"


class RemediationLevel(str, Enum):
    """Remediation level."""

    OFFICIAL_FIX = "OFFICIAL_FIX"
    REMEDIATION_NOT_DEFINED = "REMEDIATION_NOT_DEFINED"
    TEMPORARY_FIX = "TEMPORARY_FIX"
    UNAVAILABLE = "UNAVAILABLE"
    WORKAROUND = "WORKAROUND"


class ReportConfidence(str, Enum):
    """Report confidence levels."""

    CONFIDENCE_NOT_DEFINED = "CONFIDENCE_NOT_DEFINED"
    CONFIDENCE_UNKNOWN = "CONFIDENCE_UNKNOWN"
    CONFIRMED = "CONFIRMED"
    REASONABLE = "REASONABLE"


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


class Software(BaseModel):
    """Software details."""

    name: str | None = None
    version: str | None = None
    fix_version: str | None = Field(None, alias="fixVersion")
    type: SoftwareType | None = None
    vendor: str | None = None


class Cve(BaseModel):
    """CVE basic information."""

    id: str
    nvd_base_score: float | None = Field(None, alias="nvdBaseScore")
    risk_score: float | None = Field(None, alias="riskScore")
    score: float | None = None  # Deprecated
    published_date: str | None = Field(None, alias="publishedDate")
    epss_score: float | None = Field(None, alias="epssScore")
    exploit_maturity: ExploitMaturity | None = Field(None, alias="exploitMaturity")
    exploited_in_the_wild: bool | None = Field(None, alias="exploitedInTheWild")
    remediation_level: RemediationLevel | None = Field(None, alias="remediationLevel")
    report_confidence: ReportConfidence | None = Field(None, alias="reportConfidence")


class S1BaseValues(BaseModel):
    """SentinelOne base values."""

    attack_vector: str | None = Field(None, alias="attackVector")
    attack_complexity: str | None = Field(None, alias="attackComplexity")
    privileges_required: str | None = Field(None, alias="privilegesRequired")
    user_interactions: str | None = Field(None, alias="userInteractions")
    scope: str | None = None
    confidentiality: str | None = None
    integrity: str | None = None
    availability: str | None = None


class RiskIndicators(BaseModel):
    """Risk indicators."""

    severity: VulnerabilitySeverity | None = None
    values: list[str] = Field(default_factory=list)


class CveTimelineItem(BaseModel):
    """CVE timeline item."""

    date: str | None = None
    key: str | None = None


class CveDetail(BaseModel):
    """CVE detail information."""

    id: str
    description: str
    nvd_base_score: float | None = Field(None, alias="nvdBaseScore")
    risk_score: float | None = Field(None, alias="riskScore")
    score: float | None = None
    published_date: str | None = Field(None, alias="publishedDate")
    epss_score: float | None = Field(None, alias="epssScore")
    epss_percentile: float | None = Field(None, alias="epssPercentile")
    epss_last_updated_date: str | None = Field(None, alias="epssLastUpdatedDate")
    exploit_maturity: ExploitMaturity | None = Field(None, alias="exploitMaturity")
    exploited_in_the_wild: bool | None = Field(None, alias="exploitedInTheWild")
    kev_available: bool | None = Field(None, alias="kevAvailable")
    remediation_level: RemediationLevel | None = Field(None, alias="remediationLevel")
    report_confidence: ReportConfidence | None = Field(None, alias="reportConfidence")
    s1_base_values: S1BaseValues | None = Field(None, alias="s1BaseValues")
    risk_indicators: list[RiskIndicators] | None = Field(None, alias="riskIndicators")
    mitre_reference_url: str | None = Field(None, alias="mitreReferenceUrl")
    nvd_reference_url: str | None = Field(None, alias="nvdReferenceUrl")
    timeline: list[CveTimelineItem] | None = None


class FindingData(BaseModel):
    """Finding data."""

    context: dict[str, object] | None = None


class Vulnerability(BaseModel):
    """Main vulnerability model.

    All fields except 'id' are optional to support dynamic field selection.
    When using custom field selection, only requested fields will be populated.
    """

    id: str
    name: str | None = None
    severity: VulnerabilitySeverity | None = None
    status: Status | None = None
    asset: Asset | None = None
    scope: Scope | None = None
    cve: Cve | None = None
    software: Software | None = None
    product: str | None = None
    vendor: str | None = None
    detected_at: str | None = Field(None, alias="detectedAt")
    last_seen_at: str | None = Field(None, alias="lastSeenAt")

    # Optional fields
    analyst_verdict: AnalystVerdict | None = Field(None, alias="analystVerdict")
    assignee: User | None = None
    exclusion_policy_id: str | None = Field(None, alias="exclusionPolicyId")


class VulnerabilityDetail(BaseModel):
    """Vulnerability detail model with full information."""

    id: str
    external_id: str = Field(alias="externalId")
    name: str
    severity: VulnerabilitySeverity
    status: Status
    asset: Asset
    scope: Scope
    scope_level: AssetScopeLevel = Field(alias="scopeLevel")
    cve: CveDetail
    software: Software
    product: str
    vendor: str
    detected_at: str = Field(alias="detectedAt")
    last_seen_at: str | None = Field(None, alias="lastSeenAt")
    updated_at: str | None = Field(None, alias="updatedAt")
    finding_data: FindingData = Field(alias="findingData")
    paid_scope: bool = Field(alias="paidScope")
    remediation_insights_available: bool = Field(alias="remediationInsightsAvailable")
    self_link: str | None = Field(None, alias="selfLink")

    # Optional fields
    analyst_verdict: AnalystVerdict | None = Field(None, alias="analystVerdict")
    assignee: User | None = None
    exclusion_policy_id: str | None = Field(None, alias="exclusionPolicyId")


class PageInfo(BaseModel):
    """Pagination information."""

    has_next_page: bool = Field(alias="hasNextPage")
    has_previous_page: bool = Field(alias="hasPreviousPage")
    start_cursor: str | None = Field(None, alias="startCursor")
    end_cursor: str | None = Field(None, alias="endCursor")


class VulnerabilityEdge(BaseModel):
    """Vulnerability edge in a connection."""

    node: Vulnerability
    cursor: str


class VulnerabilityConnection(BaseModel):
    """Vulnerability connection for pagination."""

    edges: list[VulnerabilityEdge] = Field(default_factory=list)
    page_info: PageInfo = Field(alias="pageInfo")
    total_count: int | None = Field(None, alias="totalCount")


class VulnerabilityNote(BaseModel):
    """Vulnerability note model."""

    id: str
    vulnerability_id: str = Field(alias="vulnerabilityId")
    text: str
    author: User
    created_at: str = Field(alias="createdAt")
    updated_at: str | None = Field(None, alias="updatedAt")


class VulnerabilityNoteEdge(BaseModel):
    """Vulnerability note edge in a connection."""

    node: VulnerabilityNote
    cursor: str


class VulnerabilityNoteConnection(BaseModel):
    """Vulnerability note connection for pagination."""

    edges: list[VulnerabilityNoteEdge] = Field(default_factory=list)
    page_info: PageInfo = Field(alias="pageInfo")
    total_count: int | None = Field(None, alias="totalCount")


class VulnerabilityHistoryItem(BaseModel):
    """Vulnerability history item."""

    event_type: HistoryEventType = Field(alias="eventType")
    event_text: str = Field(alias="eventText")
    created_at: str = Field(alias="createdAt")


class VulnerabilityHistoryItemEdge(BaseModel):
    """Vulnerability history item edge in a connection."""

    node: VulnerabilityHistoryItem
    cursor: str


class VulnerabilityHistoryItemConnection(BaseModel):
    """Vulnerability history item connection for pagination."""

    edges: list[VulnerabilityHistoryItemEdge] = Field(default_factory=list)
    page_info: PageInfo = Field(alias="pageInfo")
    total_count: int | None = Field(None, alias="totalCount")


# Response wrapper models for consistency


class GetVulnerabilityResponse(BaseModel):
    """Response wrapper for get_vulnerability query."""

    vulnerability: VulnerabilityDetail


class ListVulnerabilitiesResponse(BaseModel):
    """Response wrapper for list_vulnerabilities query."""

    vulnerabilities: VulnerabilityConnection


class SearchVulnerabilitiesResponse(BaseModel):
    """Response wrapper for search_vulnerabilities query."""

    vulnerabilities: VulnerabilityConnection


class GetVulnerabilityNotesResponse(BaseModel):
    """Response wrapper for get_vulnerability_notes query."""

    vulnerability_notes: VulnerabilityNoteConnection = Field(alias="vulnerabilityNotes")


class GetVulnerabilityHistoryResponse(BaseModel):
    """Response wrapper for get_vulnerability_history query."""

    vulnerability_history: VulnerabilityHistoryItemConnection = Field(alias="vulnerabilityHistory")

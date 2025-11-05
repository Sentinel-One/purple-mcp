"""Pydantic models for Unified Asset Inventory."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Surface(str, Enum):
    """Asset surface types in Unified Asset Inventory."""

    ENDPOINT = "ENDPOINT"
    CLOUD = "CLOUD"
    IDENTITY = "IDENTITY"
    NETWORK_DISCOVERY = "NETWORK_DISCOVERY"


class InventoryNote(BaseModel):
    """A note associated with an inventory item."""

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    note: str | None = None
    resource_id: str | None = Field(None, alias="resourceId")
    created_at: str | None = Field(None, alias="createdAt")
    updated_at: str | None = Field(None, alias="updatedAt")
    user_id: str | None = Field(None, alias="userId")
    user_name: str | None = Field(None, alias="userName")


class DeviceReviewLog(BaseModel):
    """Device review log entry."""

    model_config = ConfigDict(populate_by_name=True)

    current: str | None = None
    previous: str | None = None
    reason: str | None = None
    reason_details: str | None = Field(None, alias="reasonDetails")
    updated_time: int | None = Field(None, alias="updatedTime")
    updated_time_dt: str | None = Field(None, alias="updatedTimeDt")
    username: str | None = None


class NetworkInterface(BaseModel):
    """Network interface information."""

    model_config = ConfigDict(populate_by_name=True)

    gateway_ip: str | None = Field(None, alias="gatewayIp")
    gateway_mac: str | None = Field(None, alias="gatewayMac")
    ip: str | None = None
    mac: str | None = None
    network_name: str | None = Field(None, alias="networkName")
    subnet: str | None = None
    name: str | None = None


class InventoryItem(BaseModel):
    """Unified Asset Inventory item with comprehensive field coverage.

    This model covers fields from multiple response mixins in the source schema.
    All fields are optional as different resource types have different available fields.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    # Core/Common fields (CommonResponseMixin)
    id: str | None = None
    id_secondary: list[str] | None = Field(None, alias="idSecondary")
    name: str | None = None
    tags: list[dict[str, str | bool]] | None = None

    # Asset fields (AssetResponseMixin)
    active_coverage: list[str] | None = Field(None, alias="activeCoverage")
    asset_contact_email: str | None = Field(None, alias="assetContactEmail")
    asset_criticality: str | None = Field(None, alias="assetCriticality")
    asset_environment: str | None = Field(None, alias="assetEnvironment")
    asset_status: str | None = Field(None, alias="assetStatus")
    category: str | None = None
    device_review: str | None = Field(None, alias="deviceReview")
    device_review_log: list[DeviceReviewLog] | None = Field(None, alias="deviceReviewLog")
    missing_coverage: list[str] | None = Field(None, alias="missingCoverage")
    notes: list[InventoryNote] | None = None
    resource_type: str | None = Field(None, alias="resourceType")
    risk_factors: list[str] | None = Field(None, alias="riskFactors")
    sub_category: str | None = Field(None, alias="subCategory")
    surfaces: list[str] | None = None
    infection_status: str | None = Field(None, alias="infectionStatus")
    last_active_dt: str | None = Field(None, alias="lastActiveDt")

    # Cloud fields (CloudResponsesMixin)
    cloud_provider_account_id: str | None = Field(None, alias="cloudProviderAccountId")
    cloud_provider_account_name: str | None = Field(None, alias="cloudProviderAccountName")
    cloud_provider_organization: str | None = Field(None, alias="cloudProviderOrganization")
    cloud_provider_organization_unit: str | None = Field(
        None, alias="cloudProviderOrganizationUnit"
    )
    cloud_provider_organization_unit_path: str | None = Field(
        None, alias="cloudProviderOrganizationUnitPath"
    )
    cloud_provider_project_id: str | None = Field(None, alias="cloudProviderProjectId")
    cloud_provider_resource_group: str | None = Field(None, alias="cloudProviderResourceGroup")
    cloud_provider_subscription_id: str | None = Field(None, alias="cloudProviderSubscriptionId")
    cloud_tags: list[dict[str, str | bool]] | None = Field(None, alias="cloudTags")
    created_time: str | None = Field(None, alias="createdTime")
    region: str | None = None
    source_json: dict[str, object] | None = Field(None, alias="sourceJson")
    cloud_provider_url_string: str | None = Field(None, alias="cloudProviderUrlString")
    cloud_resource_id: str | None = Field(None, alias="cloudResourceId")
    cloud_resource_uid: str | None = Field(None, alias="cloudResourceUid")
    cloud_resource_arn: str | None = Field(None, alias="cloudResourceArn")

    # Compute Device fields (ComputeDeviceResponseMixin)
    architecture: str | None = None
    core_count: int | None = Field(None, alias="coreCount")
    domain: str | None = None
    gateway_ips: list[str] | None = Field(None, alias="gatewayIps")
    gateway_macs: list[str] | None = Field(None, alias="gatewayMacs")
    hostnames: list[str] | None = None
    internal_ips: list[str] | None = Field(None, alias="internalIps")
    internal_ips_v6: list[str] | None = Field(None, alias="internalIpsV6")
    ip_address: str | None = Field(None, alias="ipAddress")
    mac_addresses: list[str] | None = Field(None, alias="macAddresses")
    memory: int | None = None
    memory_readable: str | None = Field(None, alias="memoryReadable")
    network_interfaces: list[NetworkInterface] | None = Field(None, alias="networkInterfaces")
    os: str | None = None
    os_family: str | None = Field(None, alias="osFamily")
    os_version: str | None = Field(None, alias="osVersion")
    os_name_version: str | None = Field(None, alias="osNameVersion")
    subnets: list[str] | None = None
    instance_id: str | None = Field(None, alias="instanceId")
    network_security_groups: list[str] | None = Field(None, alias="networkSecurityGroups")

    # Cloud Compute Device fields (CloudComputeDeviceResponseMixin)
    image_id: str | None = Field(None, alias="imageId")
    instance_type: str | None = Field(None, alias="instanceType")
    instance_role: str | None = Field(None, alias="instanceRole")
    subnet_id: list[str] | None = Field(None, alias="subnetId")
    virtual_network_id: str | None = Field(None, alias="virtualNetworkId")

    # EPP Endpoint fields (EppEndpointResponsesMixin)
    agent: dict[str, object] | None = None
    identity: dict[str, object] | None = None
    cpu: str | None = None
    last_reboot_dt: str | None = Field(None, alias="lastRebootDt")
    first_seen_dt: str | None = Field(None, alias="firstSeenDt")
    serial_number: str | None = Field(None, alias="serialNumber")
    is_ad_connector: bool | None = Field(None, alias="isAdConnector")
    is_dc_server: bool | None = Field(None, alias="isDcServer")
    legacy_identity_policy_name: str | None = Field(None, alias="legacyIdentityPolicyName")
    ads_enabled: bool | None = Field(None, alias="adsEnabled")
    model_name: str | None = Field(None, alias="modelName")
    os_username: str | None = Field(None, alias="osUsername")
    aws_ecs_info: dict[str, object] | None = Field(None, alias="awsEcsInfo")

    # Ranger Device fields (RangerDeviceResponseMixin)
    detected_from_site: str | None = Field(None, alias="detectedFromSite")
    discovery_methods: list[str] | None = Field(None, alias="discoveryMethods")
    last_update_dt: str | None = Field(None, alias="lastUpdateDt")
    manufacturer: str | None = None
    network_name: str | None = Field(None, alias="networkName")
    network_names: list[str] | None = Field(None, alias="networkNames")
    previous_device_function: str | None = Field(None, alias="previousDeviceFunction")
    previous_os_type: str | None = Field(None, alias="previousOsType")
    previous_os_version: str | None = Field(None, alias="previousOsVersion")
    ranger_tags: list[str] | None = Field(None, alias="rangerTags")
    tcp_ports: list[str] | None = Field(None, alias="tcpPorts")
    udp_ports: list[str] | None = Field(None, alias="udpPorts")
    epp_unsupported_unknown: str | None = Field(None, alias="eppUnsupportedUnknown")

    # SentinelOne metadata fields (SentinelOneMetadataResponseMixin)
    s1_account_name: str | None = Field(None, alias="s1AccountName")
    s1_group_name: str | None = Field(None, alias="s1GroupName")
    s1_site_name: str | None = Field(None, alias="s1SiteName")
    s1_updated_at: str | None = Field(None, alias="s1UpdatedAt")
    s1_scope_id: str | None = Field(None, alias="s1ScopeId")
    s1_scope_level: str | None = Field(None, alias="s1ScopeLevel")
    s1_scope_path: str | None = Field(None, alias="s1ScopePath")
    s1_management_id: int | None = Field(None, alias="s1ManagementId")
    s1_account_id: str | None = Field(None, alias="s1AccountId")
    s1_site_id: str | None = Field(None, alias="s1SiteId")
    s1_group_id: str | None = Field(None, alias="s1GroupId")
    s1_scope_type: int | None = Field(None, alias="s1ScopeType")

    # SentinelOne Alerts fields (SentinelOneAlertsResponseMixin)
    alerts: list[dict[str, object]] | None = None
    alerts_count: list[dict[str, object]] | None = Field(None, alias="alertsCount")

    # Kubernetes fields (KubernetesResponseSchemaMixin)
    k8s_cluster: str | None = Field(None, alias="k8sCluster")
    k8s_node: str | None = Field(None, alias="k8sNode")
    k8s_node_labels: list[str] | None = Field(None, alias="k8sNodeLabels")
    k8s_type: str | None = Field(None, alias="k8sType")
    k8s_version: str | None = Field(None, alias="k8sVersion")
    k8s_cns_enabled: bool | None = Field(None, alias="k8sCnsEnabled")
    k8s_cws_enabled: bool | None = Field(None, alias="k8sCwsEnabled")
    k8s_helper_agent_deployed: bool | None = Field(None, alias="k8sHelperAgentDeployed")
    k8s_annotations: list[str] | None = Field(None, alias="k8sAnnotations")
    k8s_cluster_id: str | None = Field(None, alias="k8sClusterId")
    k8s_namespace: str | None = Field(None, alias="k8sNamespace")
    k8s_resource_id: str | None = Field(None, alias="k8sResourceId")
    k8s_source_json: dict[str, object] | None = Field(None, alias="k8sSourceJson")
    k8s_running_on_nodes: list[str] | None = Field(None, alias="k8sRunningOnNodes")

    # AWS EC2 Instance fields (AwsEc2InstanceResponseMixin)
    is_rogue: bool | None = Field(None, alias="isRogue")
    state: str | None = None

    # AWS S3 Bucket fields (AwsS3BucketResponseMixin)
    allows_unencrypted_object_uploads: bool | None = Field(
        None, alias="allowsUnencryptedObjectUploads"
    )
    encryption_type: list[str] | None = Field(None, alias="encryptionType")
    object_count: int | None = Field(None, alias="objectCount")
    policy_document: str | None = Field(None, alias="policyDocument")
    realtime_malware_protection_enabled_time: str | None = Field(
        None, alias="realtimeMalwareProtectionEnabledTime"
    )

    # CDS fields (CdsResponseMixin)
    scan_status: str | None = Field(None, alias="scanStatus")
    last_scan_dt: str | None = Field(None, alias="lastScanDt")
    threat_detection_status: str | None = Field(None, alias="threatDetectionStatus")
    threat_detection_policy_status: str | None = Field(None, alias="threatDetectionPolicyStatus")

    # DSPM fields (DspmResponseMixin)
    connectivity_status: str | None = Field(None, alias="connectivityStatus")
    data_classification_status: str | None = Field(None, alias="dataClassificationStatus")
    data_classification_policy_status: str | None = Field(
        None, alias="dataClassificationPolicyStatus"
    )
    data_types: list[str] | None = Field(None, alias="dataTypes")
    data_classification_categories: list[str] | None = Field(
        None, alias="dataClassificationCategories"
    )
    has_classified_data: bool | None = Field(None, alias="hasClassifiedData")
    data_classification_scan_status: str | None = Field(None, alias="dataClassificationScanStatus")
    data_classification_last_scan_dt: str | None = Field(
        None, alias="dataClassificationLastScanDt"
    )

    # Cloud Storage fields (CloudStorageResponsesMixin)
    backup_enabled: bool | None = Field(None, alias="backupEnabled")
    backup_retention_period: str | None = Field(None, alias="backupRetentionPeriod")
    backup_retention_period_days: int | None = Field(None, alias="backupRetentionPeriodDays")
    encryption_enabled: bool | None = Field(None, alias="encryptionEnabled")
    engine_type: str | None = Field(None, alias="engineType")
    engine_version: str | None = Field(None, alias="engineVersion")
    firewall_rules_enabled: bool | None = Field(None, alias="firewallRulesEnabled")
    high_availability_enabled: bool | None = Field(None, alias="highAvailabilityEnabled")
    is_public: bool | None = Field(None, alias="isPublic")
    logging_enabled: bool | None = Field(None, alias="loggingEnabled")
    machine_type: str | None = Field(None, alias="machineType")
    monitoring_enabled: bool | None = Field(None, alias="monitoringEnabled")
    multi_az_enabled: bool | None = Field(None, alias="multiAzEnabled")
    replication_enabled: bool | None = Field(None, alias="replicationEnabled")
    storage_class: str | None = Field(None, alias="storageClass")
    storage_size: str | None = Field(None, alias="storageSize")
    storage_type: str | None = Field(None, alias="storageType")
    versioning_enabled: bool | None = Field(None, alias="versioningEnabled")
    virtual_network_rules_enabled: bool | None = Field(None, alias="virtualNetworkRulesEnabled")

    # AD Entity fields (ADEntityResponseSchemaMixin)
    admin_count: int | None = Field(None, alias="adminCount")
    cn: str | None = None
    display_name: str | None = Field(None, alias="displayName")
    distinguished_name: str | None = Field(None, alias="distinguishedName")
    forest: str | None = None
    deleted: bool | None = None
    member_of: list[str] | None = Field(None, alias="memberOf")
    member_of_transitive: list[str] | None = Field(None, alias="memberOfTransitive")
    principal_name: str | None = Field(None, alias="principalName")
    nt_security_descriptor: str | None = Field(None, alias="ntSecurityDescriptor")
    object_category: str | None = Field(None, alias="objectCategory")
    object_class: list[str] | None = Field(None, alias="objectClass")
    object_guid: str | None = Field(None, alias="objectGuid")
    object_sid: str | None = Field(None, alias="objectSid")
    sam_account_name: str | None = Field(None, alias="samAccountName")
    service_account: bool | None = Field(None, alias="serviceAccount")
    service_principal_name: list[str] | None = Field(None, alias="servicePrincipalName")
    sid_history: list[str] | None = Field(None, alias="sidHistory")
    usn_changed: int | None = Field(None, alias="usnChanged")
    usn_created: int | None = Field(None, alias="usnCreated")
    privileged: bool | None = None
    member_of_guid: list[str] | None = Field(None, alias="memberOfGuid")

    # Identity User fields (IdentityUserResponseSchemaMixin)
    account_expires: str | None = Field(None, alias="accountExpires")
    bad_password_time: str | None = Field(None, alias="badPasswordTime")
    bad_password_count: int | None = Field(None, alias="badPasswordCount")
    enabled: bool | None = None
    last_known_parent: str | None = Field(None, alias="lastKnownParent")
    last_logon_time: str | None = Field(None, alias="lastLogonTime")
    last_modified_time: str | None = Field(None, alias="lastModifiedTime")
    lock_out_time: str | None = Field(None, alias="lockOutTime")
    logon_count: int | None = Field(None, alias="logonCount")
    logon_hours: str | None = Field(None, alias="logonHours")
    mail: str | None = None
    consistency_guid: str | None = Field(None, alias="consistencyGuid")
    creator_sid: str | None = Field(None, alias="creatorSid")
    allowed_to_act_on_behalf_of_other_identity: bool | None = Field(
        None, alias="allowedToActOnBehalfOfOtherIdentity"
    )
    allowed_to_delegate_to: list[str] | None = Field(None, alias="allowedToDelegateTo")
    parent_dist_name: str | None = Field(None, alias="parentDistName")
    resultant_pso: str | None = Field(None, alias="resultantPso")
    user_password_expiry_time_computed: str | None = Field(
        None, alias="userPasswordExpiryTimeComputed"
    )
    password_never_expire: bool | None = Field(None, alias="passwordNeverExpire")
    primary_group_id: int | None = Field(None, alias="primaryGroupId")
    password_last_set_time: str | None = Field(None, alias="passwordLastSetTime")
    recycled: bool | None = None
    user_principal_name: str | None = Field(None, alias="userPrincipalName")
    user_account_control: int | None = Field(None, alias="userAccountControl")
    sam_account_type: int | None = Field(None, alias="samAccountType")
    token_groups: list[str] | None = Field(None, alias="tokenGroups")

    # Entra ID fields (EntraIdEntityResponseSchemaMixin)
    account_status: bool | None = Field(None, alias="accountStatus")
    age_group: str | None = Field(None, alias="ageGroup")
    deleted_time: str | None = Field(None, alias="deletedTime")
    department: str | None = None
    employee_type: str | None = Field(None, alias="employeeType")
    given_name: str | None = Field(None, alias="givenName")
    job_title: str | None = Field(None, alias="jobTitle")
    on_premises_distinguished_name: str | None = Field(None, alias="onPremisesDistinguishedName")
    on_premises_domain_name: str | None = Field(None, alias="onPremisesDomainName")
    on_premises_immutable_id: str | None = Field(None, alias="onPremisesImmutableId")
    on_premises_last_sync_time: str | None = Field(None, alias="onPremisesLastSyncTime")
    on_premises_sam_account_name: str | None = Field(None, alias="onPremisesSamAccountName")
    on_premises_sync_enabled: str | None = Field(None, alias="onPremisesSyncEnabled")
    on_premises_user_principal_name: str | None = Field(None, alias="onPremisesUserPrincipalName")
    other_mails: list[str] | None = Field(None, alias="otherMails")
    proxy_addresses: list[str] | None = Field(None, alias="proxyAddresses")
    on_premises_security_identifier: str | None = Field(None, alias="onPremisesSecurityIdentifier")
    office_location: str | None = Field(None, alias="officeLocation")
    surname: str | None = None
    classification: str | None = None
    expiration_time: str | None = Field(None, alias="expirationTime")
    security_enabled: str | None = Field(None, alias="securityEnabled")
    unique_name: str | None = Field(None, alias="uniqueName")
    visibility: str | None = None
    force_change_password_next_signin: bool | None = Field(
        None, alias="forceChangePasswordNextSignin"
    )
    force_change_password_next_signin_with_mfa: bool | None = Field(
        None, alias="forceChangePasswordNextSigninWithMfa"
    )
    last_password_change_time: str | None = Field(None, alias="lastPasswordChangeTime")
    entraid_group_type: str | None = Field(None, alias="entraidGroupType")


class PaginationInfo(BaseModel):
    """Pagination information for inventory response."""

    model_config = ConfigDict(populate_by_name=True)

    total_count: int | None = Field(None, alias="totalCount")
    limit: int | None = None
    skip: int | None = None


class InventoryResponse(BaseModel):
    """Response from inventory API containing items and pagination info."""

    model_config = ConfigDict(populate_by_name=True)

    data: list[InventoryItem] = Field(default_factory=list)
    pagination: PaginationInfo | None = None

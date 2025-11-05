"""GraphQL query templates for the misconfigurations API.

This module contains all GraphQL query templates used by the MisconfigurationsClient
to interact with the XSPM Misconfigurations service.
"""

import re
import textwrap
from string import Template

from purple_mcp.libs.graphql_utils import GraphQLFieldCatalog


def _normalize_fragment(text: str) -> str:
    """Normalize a multi-line fragment to a single-line GraphQL string.

    Converts newlines to spaces and normalizes multiple spaces to single spaces.
    """
    # Replace newlines with spaces, strip, and normalize multiple spaces
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def _build_asset_fragment() -> str:
    """Build the asset fragment for default field selection.

    Includes: id, externalId, name, type, category, subcategory, privileged,
              cloudInfo (accountId, accountName, providerName, region),
              kubernetesInfo (cluster, namespace)
    """
    return _normalize_fragment(
        textwrap.dedent(
            """
        asset {
            id
            externalId
            name
            type
            category
            subcategory
            privileged
            cloudInfo {
                accountId
                accountName
                providerName
                region
            }
            kubernetesInfo {
                cluster
                namespace
            }
        }
        """
        )
    )


def _build_scope_fragment() -> str:
    """Build the scope fragment for default field selection.

    Includes: account (id, name), site (id, name), group (id, name)
    """
    return _normalize_fragment(
        textwrap.dedent(
            """
        scope {
            account {
                id
                name
            }
            site {
                id
                name
            }
            group {
                id
                name
            }
        }
        """
        )
    )


def _build_cnapp_fragment() -> str:
    """Build the cnapp fragment for default field selection.

    Includes: policy (id, version, group), verifiedExploitable
    """
    return _normalize_fragment(
        textwrap.dedent(
            """
        cnapp {
            policy {
                id
                version
                group
            }
            verifiedExploitable
        }
        """
        )
    )


def _build_evidence_fragment() -> str:
    """Build the evidence fragment for default field selection.

    Includes: fileName, fileType, iacFramework, ipAddress, port, subdomain
    """
    return _normalize_fragment(
        textwrap.dedent(
            """
        evidence {
            fileName
            fileType
            iacFramework
            ipAddress
            port
            subdomain
        }
        """
        )
    )


def _build_mitre_attacks_fragment() -> str:
    """Build the mitreAttacks fragment for default field selection.

    Includes: techniqueId, techniqueName, techniqueUrl, tacticName, tacticUid
    """
    return _normalize_fragment(
        textwrap.dedent(
            """
        mitreAttacks {
            techniqueId
            techniqueName
            techniqueUrl
            tacticName
            tacticUid
        }
        """
        )
    )


def _build_remediation_fragment() -> str:
    """Build the remediation fragment for default field selection.

    Includes: mitigable, mitigationSteps
    """
    return _normalize_fragment(
        textwrap.dedent(
            """
        remediation {
            mitigable
            mitigationSteps
        }
        """
        )
    )


def _build_admission_request_fragment() -> str:
    """Build the admissionRequest fragment for default field selection.

    Includes: category, resourceName, resourceNamespace, resourceType,
              userName, userUid, userGroup
    """
    return _normalize_fragment(
        textwrap.dedent(
            """
        admissionRequest {
            category
            resourceName
            resourceNamespace
            resourceType
            userName
            userUid
            userGroup
        }
        """
        )
    )


# Unified field configuration for misconfigurations
MISCONFIGURATION_FIELD_CATALOG = GraphQLFieldCatalog(
    default_fields=[
        "id",
        "externalId",
        "name",
        "severity",
        "status",
        "detectedAt",
        "eventTime",
        "lastSeenAt",
        "environment",
        "product",
        "vendor",
        _build_asset_fragment(),
        _build_scope_fragment(),
        "analystVerdict",
        "assignee { id email fullName }",
        _build_cnapp_fragment(),
        "complianceStandards",
        "dataClassificationCategories",
        "dataClassificationDataTypes",
        "enforcementAction",
        _build_evidence_fragment(),
        "exclusionPolicyId",
        "exploitId",
        "exposureReason",
        "findingType",  # Deprecated in favor of misconfigurationType
        "mitigable",
        "misconfigurationType",
        _build_mitre_attacks_fragment(),
        "organization",
        _build_remediation_fragment(),
        "resourceUid",
        _build_admission_request_fragment(),
    ],
    description="Misconfiguration field configuration for XSPM GraphQL API",
)

# Legacy export for backward compatibility
DEFAULT_MISCONFIGURATION_FIELDS: list[str] = MISCONFIGURATION_FIELD_CATALOG.default_fields


# GraphQL query templates
GET_MISCONFIGURATION_QUERY = """
query GetMisconfiguration($id: ID!) {
    misconfiguration(id: $id) {
        id
        externalId
        name
        description
        severity
        status
        detectedAt
        eventTime
        lastSeenAt
        environment
        product
        vendor
        asset {
            id
            externalId
            name
            type
            category
            subcategory
            domain
            agentUuid
            privileged
            criticality
            osType
            cloudInfo {
                accountId
                accountName
                providerName
                region
                resourceId
                resourceLink
            }
            kubernetesInfo {
                cluster
                clusterId
                namespace
            }
        }
        scope {
            account {
                id
                name
            }
            site {
                id
                name
            }
            group {
                id
                name
            }
        }
        scopeLevel
        analystVerdict
        assignee {
            id
            email
            fullName
            deleted
        }
        cnapp {
            policy {
                id
                name
                description
                version
                group
            }
            verifiedExploitable
            autoRemediation
            haConnectionId
            haTemplateId
        }
        compliance {
            standards
            requirements
            complianceStandards {
                title
                url
            }
            complianceReferences {
                title
                url
            }
            status
        }
        remediation {
            mitigable
            mitigationSteps
            references {
                title
                url
            }
        }
        failedRules {
            name
            description
            severity
            impact
            compliance
            recommendedAction
            enforcementSettings
        }
        findingData {
            properties {
                name
                value
            }
            exposureReason
            context
        }
        mitreAttacks {
            techniqueId
            techniqueName
            techniqueUrl
            tacticName
            tacticUid
        }
        dataClassificationCategories
        dataClassificationDataTypes
        enforcementAction
        evidence {
            fileName
            fileType
            fileUrl
            iacFramework
            ipAddress
            port
            subdomain
            commitedBy
            secret {
                type
                hash
                valid
            }
        }
        exclusionPolicyId
        exploitId
        exposureId
        misconfigurationType
        organization
        resourceUid
        selfLink
        admissionRequest {
            category
            resourceName
            resourceNamespace
            resourceType
            userName
            userUid
            userGroup
        }
    }
}
"""

LIST_MISCONFIGURATIONS_QUERY_TEMPLATE = Template(
    """
query ListMisconfigurations($first: Int!, $after: String${view_type_param}) {
    misconfigurations(first: $first, after: $after${view_type_arg}) {
        edges {
            node {
${node_fields}
            }
            cursor
        }
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
        totalCount
    }
}
"""
)

SEARCH_MISCONFIGURATIONS_QUERY_TEMPLATE = Template(
    """
query SearchMisconfigurations($filters: [FilterInput!], $first: Int!, $after: String${view_type_param}) {
    misconfigurations(filters: $filters, first: $first, after: $after${view_type_arg}) {
        edges {
            node {
${node_fields}
            }
            cursor
        }
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
        totalCount
    }
}
"""
)

GET_MISCONFIGURATION_NOTES_QUERY = """
query GetMisconfigurationNotes($misconfigurationId: ID!, $first: Int, $after: String) {
    misconfigurationNotes(misconfigurationId: $misconfigurationId, first: $first, after: $after) {
        edges {
            node {
                id
                misconfigurationId
                text
                author {
                    id
                    email
                    fullName
                    deleted
                }
                createdAt
                updatedAt
            }
            cursor
        }
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
        totalCount
    }
}
"""

GET_MISCONFIGURATION_HISTORY_QUERY = """
query GetMisconfigurationHistory($misconfigurationId: ID!, $first: Int!, $after: String) {
    misconfigurationHistory(misconfigurationId: $misconfigurationId, first: $first, after: $after) {
        edges {
            node {
                eventType
                eventText
                createdAt
            }
            cursor
        }
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
        totalCount
    }
}
"""

"""GraphQL query templates for the vulnerabilities API.

This module contains all GraphQL query templates used by the VulnerabilitiesClient
to interact with the XSPM Vulnerabilities service.
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


def _build_cve_fragment() -> str:
    """Build the cve fragment for default field selection.

    Includes: id, nvdBaseScore, riskScore, publishedDate, epssScore,
              exploitMaturity, exploitedInTheWild
    """
    return _normalize_fragment(
        textwrap.dedent(
            """
        cve {
            id
            nvdBaseScore
            riskScore
            publishedDate
            epssScore
            exploitMaturity
            exploitedInTheWild
        }
        """
        )
    )


def _build_software_fragment() -> str:
    """Build the software fragment for default field selection.

    Includes: name, version, fixVersion, type, vendor
    """
    return _normalize_fragment(
        textwrap.dedent(
            """
        software {
            name
            version
            fixVersion
            type
            vendor
        }
        """
        )
    )


# Unified field configuration for vulnerabilities
VULNERABILITY_FIELD_CATALOG = GraphQLFieldCatalog(
    default_fields=[
        "id",
        "name",
        "severity",
        "status",
        "detectedAt",
        "lastSeenAt",
        "product",
        "vendor",
        _build_asset_fragment(),
        _build_scope_fragment(),
        _build_cve_fragment(),
        _build_software_fragment(),
        "analystVerdict",
        "assignee { id email fullName }",
        "exclusionPolicyId",
    ],
    description="Vulnerability field configuration for XSPM GraphQL API",
)

# Legacy export for backward compatibility
DEFAULT_VULNERABILITY_FIELDS: list[str] = VULNERABILITY_FIELD_CATALOG.default_fields


# GraphQL query templates
GET_VULNERABILITY_QUERY = """
query GetVulnerability($id: ID!) {
    vulnerability(id: $id) {
        id
        externalId
        name
        severity
        status
        detectedAt
        lastSeenAt
        updatedAt
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
        cve {
            id
            description
            nvdBaseScore
            riskScore
            score
            publishedDate
            epssScore
            epssPercentile
            epssLastUpdatedDate
            exploitMaturity
            exploitedInTheWild
            kevAvailable
            remediationLevel
            reportConfidence
            s1BaseValues {
                attackVector
                attackComplexity
                privilegesRequired
                userInteractions
                scope
                confidentiality
                integrity
                availability
            }
            riskIndicators {
                severity
                values
            }
            mitreReferenceUrl
            nvdReferenceUrl
            timeline {
                date
                key
            }
        }
        software {
            name
            version
            fixVersion
            type
            vendor
        }
        findingData {
            context
        }
        paidScope
        remediationInsightsAvailable
        selfLink
        analystVerdict
        assignee {
            id
            email
            fullName
            deleted
        }
        exclusionPolicyId
    }
}
"""

LIST_VULNERABILITIES_QUERY_TEMPLATE = Template(
    """
query ListVulnerabilities($first: Int!, $after: String) {
    vulnerabilities(first: $first, after: $after) {
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

SEARCH_VULNERABILITIES_QUERY_TEMPLATE = Template(
    """
query SearchVulnerabilities($filters: [FilterInput!], $first: Int!, $after: String) {
    vulnerabilities(filters: $filters, first: $first, after: $after) {
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

GET_VULNERABILITY_NOTES_QUERY = """
query GetVulnerabilityNotes($vulnerabilityId: ID!, $first: Int, $after: String) {
    vulnerabilityNotes(vulnerabilityId: $vulnerabilityId, first: $first, after: $after) {
        edges {
            node {
                id
                vulnerabilityId
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

GET_VULNERABILITY_HISTORY_QUERY = """
query GetVulnerabilityHistory($vulnerabilityId: ID!, $first: Int!, $after: String) {
    vulnerabilityHistory(vulnerabilityId: $vulnerabilityId, first: $first, after: $after) {
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

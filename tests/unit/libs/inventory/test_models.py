"""Unit tests for inventory models."""

from purple_mcp.libs.inventory.models import (
    DeviceReviewLog,
    InventoryItem,
    InventoryNote,
    InventoryResponse,
    NetworkInterface,
    PaginationInfo,
    Surface,
)


class TestInventoryItem:
    """Test InventoryItem model."""

    def test_inventory_item_with_boolean_tags(self) -> None:
        """Test that InventoryItem accepts tags with boolean values."""
        data = {
            "id": "test-123",
            "name": "Test Item",
            "tags": [
                {
                    "key": "environment",
                    "value": "production",
                    "read_only": True,
                    "reserved": True,
                }
            ],
        }

        item = InventoryItem.model_validate(data)
        assert item.id == "test-123"
        assert item.name == "Test Item"
        assert item.tags is not None
        assert len(item.tags) == 1
        assert item.tags[0]["key"] == "environment"
        assert item.tags[0]["value"] == "production"
        assert item.tags[0]["read_only"] is True
        assert item.tags[0]["reserved"] is True

    def test_inventory_item_with_string_tags(self) -> None:
        """Test that InventoryItem still accepts tags with all string values."""
        data = {
            "id": "test-456",
            "name": "Test Item 2",
            "tags": [
                {
                    "key": "environment",
                    "value": "staging",
                }
            ],
        }

        item = InventoryItem.model_validate(data)
        assert item.id == "test-456"
        assert item.tags is not None
        assert len(item.tags) == 1
        assert item.tags[0]["key"] == "environment"
        assert item.tags[0]["value"] == "staging"

    def test_inventory_item_with_boolean_cloud_tags(self) -> None:
        """Test that InventoryItem accepts cloud_tags with boolean values."""
        data = {
            "id": "test-789",
            "name": "Cloud Resource",
            "cloudTags": [
                {
                    "key": "managed",
                    "value": "true",
                    "system": True,
                }
            ],
        }

        item = InventoryItem.model_validate(data)
        assert item.id == "test-789"
        assert item.cloud_tags is not None
        assert len(item.cloud_tags) == 1
        assert item.cloud_tags[0]["key"] == "managed"
        assert item.cloud_tags[0]["system"] is True

    def test_inventory_item_minimal(self) -> None:
        """Test InventoryItem with minimal data."""
        data = {"id": "minimal-123"}

        item = InventoryItem.model_validate(data)
        assert item.id == "minimal-123"
        assert item.name is None
        assert item.tags is None

    def test_inventory_item_with_alias_fields(self) -> None:
        """Test InventoryItem with camelCase alias fields."""
        data = {
            "id": "alias-test",
            "idSecondary": ["secondary-1", "secondary-2"],
            "assetContactEmail": "admin@example.com",
            "assetCriticality": "HIGH",
        }

        item = InventoryItem.model_validate(data)
        assert item.id == "alias-test"
        assert item.id_secondary == ["secondary-1", "secondary-2"]
        assert item.asset_contact_email == "admin@example.com"
        assert item.asset_criticality == "HIGH"

    def test_inventory_item_allows_extra_fields(self) -> None:
        """Test that InventoryItem allows extra fields due to extra='allow' config."""
        data = {
            "id": "extra-test",
            "unknownField": "some value",
            "anotherUnknownField": 123,
        }

        # Should not raise ValidationError
        item = InventoryItem.model_validate(data)
        assert item.id == "extra-test"


class TestInventoryNote:
    """Test InventoryNote model."""

    def test_inventory_note_basic(self) -> None:
        """Test basic InventoryNote creation."""
        data = {
            "id": "note-123",
            "note": "This is a test note",
            "resourceId": "resource-456",
            "userId": "user-789",
            "userName": "Test User",
        }

        note = InventoryNote.model_validate(data)
        assert note.id == "note-123"
        assert note.note == "This is a test note"
        assert note.resource_id == "resource-456"
        assert note.user_id == "user-789"
        assert note.user_name == "Test User"


class TestDeviceReviewLog:
    """Test DeviceReviewLog model."""

    def test_device_review_log_basic(self) -> None:
        """Test basic DeviceReviewLog creation."""
        data = {
            "current": "approved",
            "previous": "pending",
            "reason": "Security review",
            "reasonDetails": "Passed all checks",
            "updatedTime": 1234567890,
            "updatedTimeDt": "2024-01-01T00:00:00Z",
            "username": "admin",
        }

        log = DeviceReviewLog.model_validate(data)
        assert log.current == "approved"
        assert log.previous == "pending"
        assert log.reason == "Security review"
        assert log.reason_details == "Passed all checks"
        assert log.updated_time == 1234567890
        assert log.username == "admin"


class TestNetworkInterface:
    """Test NetworkInterface model."""

    def test_network_interface_basic(self) -> None:
        """Test basic NetworkInterface creation."""
        data = {
            "gatewayIp": "192.168.1.1",
            "gatewayMac": "00:11:22:33:44:55",
            "ip": "192.168.1.100",
            "mac": "AA:BB:CC:DD:EE:FF",
            "networkName": "Production Network",
            "subnet": "192.168.1.0/24",
            "name": "eth0",
        }

        interface = NetworkInterface.model_validate(data)
        assert interface.gateway_ip == "192.168.1.1"
        assert interface.gateway_mac == "00:11:22:33:44:55"
        assert interface.ip == "192.168.1.100"
        assert interface.mac == "AA:BB:CC:DD:EE:FF"
        assert interface.network_name == "Production Network"
        assert interface.subnet == "192.168.1.0/24"
        assert interface.name == "eth0"


class TestPaginationInfo:
    """Test PaginationInfo model."""

    def test_pagination_info_basic(self) -> None:
        """Test basic PaginationInfo creation."""
        data = {
            "total_count": 100,
            "limit": 50,
            "skip": 0,
        }

        pagination = PaginationInfo.model_validate(data)
        assert pagination.total_count == 100
        assert pagination.limit == 50
        assert pagination.skip == 0


class TestInventoryResponse:
    """Test InventoryResponse model."""

    def test_inventory_response_basic(self) -> None:
        """Test basic InventoryResponse creation."""
        data = {
            "data": [
                {"id": "item-1", "name": "Item 1"},
                {"id": "item-2", "name": "Item 2"},
            ],
            "pagination": {
                "total_count": 2,
                "limit": 50,
                "skip": 0,
            },
        }

        response = InventoryResponse.model_validate(data)
        assert response.data is not None
        assert len(response.data) == 2
        assert response.data[0].id == "item-1"
        assert response.data[1].id == "item-2"
        assert response.pagination is not None
        assert response.pagination.total_count == 2
        assert response.pagination.limit == 50


class TestSurface:
    """Test Surface enum."""

    def test_surface_values(self) -> None:
        """Test Surface enum values."""
        assert Surface.ENDPOINT.value == "ENDPOINT"
        assert Surface.CLOUD.value == "CLOUD"
        assert Surface.IDENTITY.value == "IDENTITY"
        assert Surface.NETWORK_DISCOVERY.value == "NETWORK_DISCOVERY"

    def test_surface_from_string(self) -> None:
        """Test Surface enum from string."""
        assert Surface("ENDPOINT") == Surface.ENDPOINT
        assert Surface("CLOUD") == Surface.CLOUD
        assert Surface("IDENTITY") == Surface.IDENTITY
        assert Surface("NETWORK_DISCOVERY") == Surface.NETWORK_DISCOVERY


class TestInventoryResponseEdgeCases:
    """Test edge cases for InventoryResponse."""

    def test_inventory_response_empty_data(self) -> None:
        """Test InventoryResponse with empty data list."""
        data = {
            "data": [],
            "pagination": {"totalCount": 0, "limit": 50, "skip": 0},
        }

        response = InventoryResponse.model_validate(data)
        assert response.data == []
        assert response.pagination is not None
        assert response.pagination.total_count == 0

    def test_inventory_response_no_pagination(self) -> None:
        """Test InventoryResponse without pagination info."""
        data = {
            "data": [{"id": "test-1"}],
        }

        response = InventoryResponse.model_validate(data)
        assert len(response.data) == 1
        assert response.pagination is None

    def test_inventory_response_with_camelcase_pagination(self) -> None:
        """Test InventoryResponse with camelCase pagination fields."""
        data = {
            "data": [{"id": "test-1"}],
            "pagination": {
                "totalCount": 100,
                "limit": 50,
                "skip": 25,
            },
        }

        response = InventoryResponse.model_validate(data)
        assert response.pagination is not None
        assert response.pagination.total_count == 100
        assert response.pagination.limit == 50
        assert response.pagination.skip == 25


class TestInventoryItemComplexFields:
    """Test InventoryItem with complex nested fields."""

    def test_inventory_item_with_notes(self) -> None:
        """Test InventoryItem with notes list."""
        data = {
            "id": "item-with-notes",
            "notes": [
                {
                    "id": "note-1",
                    "note": "First note",
                    "resourceId": "item-with-notes",
                    "userId": "user-1",
                },
                {
                    "id": "note-2",
                    "note": "Second note",
                    "resourceId": "item-with-notes",
                    "userId": "user-2",
                },
            ],
        }

        item = InventoryItem.model_validate(data)
        assert item.notes is not None
        assert len(item.notes) == 2
        assert item.notes[0].id == "note-1"
        assert item.notes[0].note == "First note"
        assert item.notes[1].id == "note-2"

    def test_inventory_item_with_device_review_log(self) -> None:
        """Test InventoryItem with device review log."""
        data = {
            "id": "reviewed-device",
            "deviceReview": "approved",
            "deviceReviewLog": [
                {
                    "current": "approved",
                    "previous": "pending",
                    "reason": "Security review",
                    "updatedTime": 1234567890,
                    "username": "admin",
                }
            ],
        }

        item = InventoryItem.model_validate(data)
        assert item.device_review == "approved"
        assert item.device_review_log is not None
        assert len(item.device_review_log) == 1
        assert item.device_review_log[0].current == "approved"
        assert item.device_review_log[0].previous == "pending"

    def test_inventory_item_with_network_interfaces(self) -> None:
        """Test InventoryItem with network interfaces list."""
        data = {
            "id": "server-with-nics",
            "networkInterfaces": [
                {
                    "name": "eth0",
                    "ip": "192.168.1.100",
                    "mac": "AA:BB:CC:DD:EE:FF",
                    "subnet": "192.168.1.0/24",
                },
                {
                    "name": "eth1",
                    "ip": "10.0.0.50",
                    "mac": "11:22:33:44:55:66",
                    "subnet": "10.0.0.0/24",
                },
            ],
        }

        item = InventoryItem.model_validate(data)
        assert item.network_interfaces is not None
        assert len(item.network_interfaces) == 2
        assert item.network_interfaces[0].name == "eth0"
        assert item.network_interfaces[0].ip == "192.168.1.100"
        assert item.network_interfaces[1].name == "eth1"

    def test_inventory_item_cloud_fields(self) -> None:
        """Test InventoryItem with various cloud-specific fields."""
        data = {
            "id": "cloud-resource",
            "cloudProviderAccountId": "123456789",
            "cloudProviderAccountName": "Production Account",
            "cloudProvider": "AWS",
            "region": "us-east-1",
            "cloudResourceId": "i-1234567890abcdef0",
            "cloudResourceArn": "arn:aws:ec2:us-east-1:123456789:instance/i-1234567890abcdef0",
        }

        item = InventoryItem.model_validate(data)
        assert item.cloud_provider_account_id == "123456789"
        assert item.cloud_provider_account_name == "Production Account"
        assert item.region == "us-east-1"
        assert item.cloud_resource_id == "i-1234567890abcdef0"
        assert (
            item.cloud_resource_arn
            == "arn:aws:ec2:us-east-1:123456789:instance/i-1234567890abcdef0"
        )

    def test_inventory_item_with_list_fields(self) -> None:
        """Test InventoryItem with various list fields."""
        data = {
            "id": "item-with-lists",
            "idSecondary": ["secondary-1", "secondary-2"],
            "hostnames": ["host1.example.com", "host2.example.com"],
            "internalIps": ["10.0.0.1", "10.0.0.2"],
            "macAddresses": ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"],
            "activeCoverage": ["EPP", "EDR"],
            "missingCoverage": ["FIREWALL"],
            "riskFactors": ["OUTDATED_OS", "MISSING_PATCHES"],
        }

        item = InventoryItem.model_validate(data)
        assert item.id_secondary == ["secondary-1", "secondary-2"]
        assert item.hostnames == ["host1.example.com", "host2.example.com"]
        assert item.internal_ips == ["10.0.0.1", "10.0.0.2"]
        assert item.mac_addresses == ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"]
        assert item.active_coverage == ["EPP", "EDR"]
        assert item.missing_coverage == ["FIREWALL"]
        assert item.risk_factors == ["OUTDATED_OS", "MISSING_PATCHES"]

    def test_inventory_item_with_boolean_fields(self) -> None:
        """Test InventoryItem with various boolean fields."""
        data = {
            "id": "item-with-booleans",
            "isRogue": True,
            "isPublic": False,
            "encryptionEnabled": True,
            "loggingEnabled": False,
            "privileged": True,
            "deleted": False,
        }

        item = InventoryItem.model_validate(data)
        assert item.is_rogue is True
        assert item.is_public is False
        assert item.encryption_enabled is True
        assert item.logging_enabled is False
        assert item.privileged is True
        assert item.deleted is False


class TestPaginationInfoEdgeCases:
    """Test edge cases for PaginationInfo."""

    def test_pagination_info_with_zero_values(self) -> None:
        """Test PaginationInfo with zero values."""
        data = {"totalCount": 0, "limit": 0, "skip": 0}

        pagination = PaginationInfo.model_validate(data)
        assert pagination.total_count == 0
        assert pagination.limit == 0
        assert pagination.skip == 0

    def test_pagination_info_with_large_values(self) -> None:
        """Test PaginationInfo with large values."""
        data = {"totalCount": 1000000, "limit": 1000, "skip": 500000}

        pagination = PaginationInfo.model_validate(data)
        assert pagination.total_count == 1000000
        assert pagination.limit == 1000
        assert pagination.skip == 500000

    def test_pagination_info_partial_fields(self) -> None:
        """Test PaginationInfo with only some fields."""
        data = {"totalCount": 100}

        pagination = PaginationInfo.model_validate(data)
        assert pagination.total_count == 100
        assert pagination.limit is None
        assert pagination.skip is None

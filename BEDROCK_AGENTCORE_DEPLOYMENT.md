# Purple AI MCP - Deployment on Amazon Bedrock Agent Core

This guide will take you through deploying the Purple AI MCP Server to Amazon Bedrock AgentCore. 

## Prerequisites

**Obtain a Sentinelone Singularity Operations Center console token**

This can be found in Policy & Settings → User Management → Service Users in your console. Currently, this server only supports tokens that have access to a single Account or Site. If you need to access multiple sites, you will need to run multiple MCP servers with Account-specific or Site-specific tokens.

**Prepare Environment Variables** 

```bash
PURPLEMCP_CONSOLE_BASE_URL=https://your-console.sentinelone.net
PURPLEMCP_CONSOLE_TOKEN=your-token
MCP_MODE=streamable-http 
PURPLEMCP_STATELESS_HTTP=True
```

**Prepare AWS Environment**

### VPC Configuration

 **Outbound internet access** - Outbound internet access should be permitted through an Internet Gateway or NAT Gateway. \
 **Security Groups** - Allow outbound HTTPS on port 443 to connect to the Sentinelone service. 

It is important to note that Purple AI MCP does not include built-in authentication. For network exposed AWS deployments, ensure the MCP Server is placed behind an Application Load Balancer (ALB) with the appropriate timeout settings. Detailed information on production setups can be found [here](PRODUCTION_SETUP.md#cloud-load-balancer-setup).

### IAM Configuration

When deploying Purple AI MCP via AWS Marketplace a 'default' service role will be automatically created. To use a customer-managed service role reference the IAM Policy below.

[Trust Policy](bedrock-agentcore-trust-policy.json)
[IAM Policy](bedrock-agentcore-iam-policy.json)  

## Agent Core Configuration Settings

When configuring the MCP in Bedrock Agent core, set the following.

1. **Name** - Give the deployment a suitable name and description.
2. **Agent Source** - Default (ECR) as this is automatically populated via AWS Marketplace. 
3. **IAM Permissions** - Default service role or create a custom service role based on the IAM Configuration step [above](#iam-configuration).
4. **Protocol** - Set to MCP.
5. **Inbound Identity Type** - Select JWT (JSON Web Tokens) or IAM.
    - **JWT** - Requires IdP bearer tokens to invoke the agent.
    - **IAM** - Requires relevant IAM Permissions to invoke the agent.
6. **Security Type** - Select VPC and set the relevant VPC, Subnets & Security Groups.
7. **Advanced Settings** - Add environment variables as noted in the [prerequisites](#prerequisites).
8. Click **Host Agent** to complete the setup.

The Agent will take around ~1-2 minutes to become active.

## Useful Links

[Production VPC Setup for Purple AI MCP](PRODUCTION_SETUP.md) \
[AWS Bedrock AgentCore Overview](https://aws.amazon.com/bedrock/agentcore/) \
[Granting a VPC Internet Access via Internet Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html) \
[Creating custom IAM Roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-service.html) 


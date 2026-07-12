---
title: "Illicit Consent Grant Attacks: Weaponizing Entra ID OAuth"
description: "Deep dive into Illicit Consent Grant Attacks. Learn how actors weaponize Entra ID OAuth 2.0 for persistent access, bypassing MFA. BreachModal breaks down TTPs and provides actionable mitigation."
date: 2026-07-12T03:36:40Z
slug: "illicit-consent-grant-attacks-weaponizing-oauth-2-2"
tags: ["Illicit Consent Grant Attacks", "Entra ID OAuth security", "OAuth 2.0 exploit", "application consent phishing", "Microsoft Entra ID vulnerability", "OAuth phishing", "MFA bypass"]
author: "BreachModal Intelligence"
image: "/images/illicit-consent-grant-attacks-weaponizing-oauth-2-2.png"
---

Your organization's identity perimeter is not defined by passwords or MFA, but by the chain of OAuth 2.0 consents granted within your Entra ID tenant—a chain threat actors are now systematically breaking.

This is the reality of **Illicit Consent Grant Attacks**, a sophisticated threat vector that weaponizes the very framework designed for seamless cloud integration. Adversaries, including state-sponsored groups like APT29 (tracked by Mandiant as Nobelium), are bypassing authentication controls entirely by tricking users into authorizing malicious enterprise applications. These attacks leverage social engineering to exploit the OAuth 2.0 protocol, achieving persistent, token-based access to high-value data in Microsoft 365, often completely invisible to traditional security monitoring. The U.S. Cybersecurity and Infrastructure Security Agency (CISA) has explicitly warned of this tactic, detailing in advisory [AA22-321A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa22-321a) how threat actors abuse Microsoft's 'Verified Publisher' status to make their malicious applications appear legitimate.

Note what this means: the security model has shifted from protecting credentials to policing permissions. The very framework designed for seamless integration has become the attack vector because its default state prioritizes user convenience over explicit, risk-aware authorization. An attacker no longer needs your password if they can convince you to delegate your access rights to an application they control. This is not a failure of authentication; it is a catastrophic failure of authorization governance.


![A diagram showing the four steps of an Illicit Consent Grant Attack, from phishing email to persistent data access.](/images/illicit-consent-grant-attacks-weaponizing-oauth-2-2-visual-1.png)
*The attack chain for Illicit Consent Grant Attacks bypasses credential theft, targeting the authorization layer directly.*


## Anatomy of an Illicit Consent Grant Attack

An **Illicit Consent Grant Attack** unfolds with deceptive simplicity, making it brutally effective. The attack chain, as defined by MITRE, often involves [T1528 Steal Application Access Token](https://attack.mitre.org/techniques/T1528/) and results in a [Valid Account: Cloud Account](https://attack.mitre.org/techniques/T1078/004/) scenario, but without the need for credential theft.

First, the adversary registers a multi-tenant application with an OAuth 2.0 provider, such as Microsoft Entra ID. They configure it to request a set of highly permissive scopes—`Mail.ReadWrite`, `Files.ReadWrite.All`, `Directory.Read.All`. The application is given a benign name, like 'O365 Sync' or 'Security Update', sometimes even spoofing a legitimate service. The real malice is in the permissions requested, not the name.

Next, the attack moves to social engineering. A user receives a phishing email containing a link. The link does not lead to a credential harvesting page. Instead, it directs the user to the legitimate Microsoft identity platform URL to grant consent to the malicious application. To the user, it looks like an official, secure process. The page even bears Microsoft's branding. The only indication of compromise is the list of permissions the application is requesting—a detail most users, conditioned to click 'Accept', will overlook.

Once the user clicks 'Accept', the damage is done. The attacker's application receives an authorization code, which it exchanges for an access token and, critically, a refresh token. This refresh token allows the attacker to maintain persistent access to the user's data, generating new access tokens as needed, even if the user changes their password or has MFA enabled. The attacker now has a durable backdoor into the organization's data through the Microsoft Graph API.

> ⚠️ **BreachModal Insight:** The most dangerous aspect of this attack is its persistence. The refresh token is a long-lived bearer token that is not tied to the user's session or password. Revoking it requires an explicit administrative action against the application's service principal or the user's sessions, an action many IT teams are not equipped to perform at scale.

This attack vector turns your identity provider into a weapon against you. The very system you trust to secure your users becomes the delivery mechanism for the compromise.

## Why Entra ID OAuth Security is a Ticking Time Bomb

Microsoft Entra ID's default configuration is a primary enabler of **Illicit Consent Grant Attacks**. By default, users are permitted to consent to applications from any tenant, as long as the requested permissions are not classified as requiring administrator consent. While Microsoft has improved this posture, many legacy tenants and misconfigurations persist. This creates a massive attack surface.

According to [IBM's 2024 X-Force Threat Intelligence Index](https://www.ibm.com/reports/threat-intelligence/assets/IBM_X-Force_Threat_Intelligence_Index_2024.pdf), misconfigured cloud identity settings are a leading cause of breaches. An organization with 10,000 users, each capable of granting consent to dozens of applications over time, creates hundreds of thousands of potential authorization points. If even 0.1% of these are malicious, that represents hundreds of backdoors into corporate data. This is the practitioner's view: if you were the CISO here, you would be staring at an unmanageable web of delegated permissions, with no easy way to distinguish legitimate business tools from attacker-controlled malware.


![A simulated Entra ID audit log showing a highlighted alert for a suspicious application consent grant, a key indicator of Illicit Consent Grant Attacks.](/images/illicit-consent-grant-attacks-weaponizing-oauth-2-2-visual-2.png)
*Suspicious consent events in Entra ID audit logs are the primary indicator of a potential compromise.*


Furthermore, attackers have become adept at exploiting the trust signals within the ecosystem. The CISA alert on 'Verified Publisher' abuse is a prime example. Attackers compromise legitimate but poorly secured Microsoft Partner Network (MPN) accounts, use them to pass the publisher verification process, and then deploy malicious OAuth applications. To the end user, the application displays a trusted blue 'verified' checkmark, all but eliminating suspicion. One security researcher, upon discovering this, dryly noted that the blue checkmark had become a 'license to phish'.

> 🧠 **CISO Brief:** Your risk is not just external threats; it's the default-open posture of your cloud identity platform. A comprehensive audit of application consent policies is not an optional security project; it is a foundational requirement for operating in the cloud. You must move from a model of 'allow by default' to 'deny by default,' forcing every application consent grant to pass a risk-based review.

The systemic failure is treating application authorization as a low-risk user activity instead of a high-impact administrative action.

## Proof of Concept: Detecting and Revoking Malicious Grants

This walkthrough demonstrates how an administrator can use the Microsoft Graph PowerShell SDK to audit and remediate an Illicit Consent Grant. This is not a simulation; these are the exact commands to hunt for this threat in your own tenant.

1.  **Step 1: Connect and Authenticate**
    First, connect to Microsoft Graph with the necessary permissions to read and manage OAuth grants. You must have Application Administrator or Global Administrator privileges.
    ```powershell
    # Install the Microsoft Graph module if you haven't already
    # Install-Module Microsoft.Graph -Scope CurrentUser

    # Connect with the required permissions
    Connect-MgGraph -Scopes "OAuth2PermissionGrant.ReadWrite.All", "Application.Read.All", "Directory.Read.All"
    ```
    This command initiates a device code login and requests the scopes needed to both read all permission grants and the details of the applications they are granted to.

2.  **Step 2: Audit All Delegated Permission Grants**
    Retrieve a complete list of every delegated permission grant in your tenant. This command inventories the trust relationships between users and applications.
    ```powershell
    # Get all OAuth2 permission grants
    $grants = Get-MgOauth2PermissionGrant

    # Display the grants, focusing on key properties
    $grants | Select-Object Id, ResourceId, PrincipalId, ConsentType, Scope | Format-Table
    ```
    This output shows which user (`PrincipalId`) granted what permissions (`Scope`) to which application (`ResourceId`).

3.  **Step 3: Identify High-Risk and Suspicious Grants**
    Now, filter this list for common high-risk permissions. An attacker's application will often request broad, persistent access.
    ```powershell
    # Filter for grants containing high-risk scopes
    $riskyScopes = "Mail.ReadWrite", "Files.ReadWrite.All", "Directory.ReadWrite.All", "User.Read.All"
    $riskyGrants = $grants | Where-Object { $_.Scope -match ($riskyScopes -join '|') }

    # Correlate with application display names for easier identification
    foreach ($grant in $riskyGrants) {
        $servicePrincipal = Get-MgServicePrincipal -Filter "AppId eq '$($grant.ClientId)'"
        [PSCustomObject]@{
            GrantId = $grant.Id
            UserPrincipalName = (Get-MgUser -UserId $grant.PrincipalId).UserPrincipalName
            AppName = $servicePrincipal.DisplayName
            AppId = $servicePrincipal.AppId
            Permissions = $grant.Scope
        }
    }
    ```
    This script surfaces a human-readable list of users who have granted dangerous permissions to specific applications, allowing you to quickly spot anomalies like an unknown app with rights to read all company files.

4.  **Step 4: Revoke the Illicit Grant**
    Once a malicious grant is identified, revoke it immediately using its unique object ID.
    ```powershell
    # Replace 'grant-object-id' with the actual GrantId from the previous step
    $grantToRevoke = "grant-object-id"

    # Remove the specific permission grant
    Remove-MgOauth2PermissionGrant -OAuth2PermissionGrantId $grantToRevoke

    Write-Host "Successfully revoked grant with ID: $grantToRevoke" -ForegroundColor Green
    ```
    This command severs the connection between the user and the malicious application, rendering the attacker's refresh token invalid.

> 🧩 **Tactical Note:** After revoking the grant, you must also disable the associated Enterprise Application (Service Principal) in Entra ID to prevent it from being granted new permissions. Additionally, revoke all refresh tokens for the compromised user account to terminate any existing sessions.

## FINAL VERDICT

The final verdict on **Illicit Consent Grant Attacks** is that they represent a fundamental failure of trust management in the cloud. The burden of this risk falls squarely on security leaders who have not shifted their focus from authentication to authorization governance. The convenience of OAuth 2.0 has created a culture of casual consent, and threat actors are capitalizing on this systemic weakness with devastating efficiency. The only path forward is a Zero Trust model applied to applications themselves, where every consent grant is treated as a high-privilege event requiring explicit, risk-based approval through a mandatory admin consent workflow.

Organizations that fail to implement strict controls on application consent are not just misconfigured; they are operating with an open invitation for an account takeover that bypasses their most expensive security controls. BreachModal's Adversarial Simulation and Cloud Security Posture Management services are designed to identify and remediate these exact authorization flaws before they become a breach. **Contact us to assess your Entra ID tenant's true attack surface.**
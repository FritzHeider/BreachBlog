---
title: "Iranian Cyberattacks on US Water Utilities: A CISO's Guide"
description: "In-depth analysis of Iranian-linked cyberattacks targeting US water utilities. Learn how IRGC-affiliated groups exploit PLCs and how to mitigate the threat."
date: 2026-08-04T19:01:57Z
slug: "iranian-linked-cyberattacks-targeting-us-water"
tags: ["iranian cyberattacks us water utilities", "cyberav3ngers attacks", "unitronics plc vulnerability", "critical infrastructure cybersecurity", "water system security", "ot security best practices", "irgc cyber threats"]
author: "BreachModal Intelligence"
image: "/images/iranian-linked-cyberattacks-targeting-us-water.png"
---

Iranian state-sponsored actors are actively compromising US water systems because our nation's most critical infrastructure is built on decades-old, internet-exposed technology secured by default passwords.

This is not theoretical. A threat group calling itself "CyberAv3ngers," which federal authorities link to the Iranian Islamic Revolutionary Guard Corps Cyber-Electronic Command (IRGC CEC), has been systematically targeting and disrupting water and wastewater systems (WWS). According to a [joint advisory from CISA, the FBI, and the EPA (AA23-335A)](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-335a), these actors are exploiting exposed Programmable Logic Controllers (PLCs), specifically targeting Israeli-made Unitronics Vision Series PLCs. The attackers' methods are brutally simple: they scan the internet for these devices, log in using default factory credentials, and then manipulate operations, in some cases defacing the Human Machine Interface (HMI) with anti-Israel messages.

Note what this means: A geopolitical conflict in the Middle East is now directly causing operational shutdowns of municipal services in the American heartland. This is happening not because of a sophisticated zero-day exploit, but because of a systemic, decades-long failure to invest in and secure the operational technology (OT) that underpins modern life. The economic incentive for small, underfunded utilities has been to prioritize uptime over security, creating a vast, vulnerable attack surface that state actors are now gleefully exploiting.


![Diagram showing the attack chain of Iranian cyberattacks on US water utilities, from internet scanning to compromising exposed PLCs.](/images/iranian-linked-cyberattacks-targeting-us-water-visual-1.png)
*The attack path from state-sponsored actor to physical disruption relies on publicly accessible tools and basic security oversights.*


## The Anatomy of an Attack: From Shodan to Shutdown

The attack chain used in the recent campaign against US water utilities is a textbook example of exploiting basic security hygiene failures. It demonstrates a low-cost, high-impact strategy that requires minimal sophistication.

First, the actors, identified by Microsoft as Storm-0784 and by others as Hydro Kitten, use public scanning tools like Shodan to identify internet-accessible PLCs and HMIs. These devices, which directly control pumps, valves, and other physical processes, should never be directly reachable from the public internet. Researchers have found them exposed on common OT ports like 502 (Modbus), 102 (Siemens S7), and 44818 (EtherNet/IP). According to CISA, the Unitronics devices were often exposed with their default password, which is publicly known and easily guessed.

Second, upon gaining access, the attackers leverage the device's own functionality to cause disruption. This isn't malware deployment; it's authorized users performing unauthorized actions. They have been observed changing administrator passwords to lock out legitimate operators, altering settings to disrupt water pressure, and defacing the HMI screens. In one documented case in Aliquippa, Pennsylvania, operators arrived to find their systems commandeered and displaying a CyberAv3ngers calling card. It’s a sobering reminder that a multi-million dollar water treatment plant can be brought to its knees by a password that was never changed from '1111'.

This direct manipulation of OT systems is a dangerous escalation. It moves beyond data theft into the realm of physical sabotage, a line that nation-state actors are now crossing with alarming frequency.

> 🧠 CISO Brief: Your OT and IT networks must be rigorously segmented. An attacker compromising your corporate email should have zero path to a PLC controlling a water pump. If you cannot produce a network diagram proving this separation, you have a critical, unmitigated risk.

## The Actors: Who are the CyberAv3ngers?

The group claiming responsibility, "CyberAv3ngers," is assessed by US intelligence agencies to be a front for Iran's IRGC. This affiliation places their activities squarely in the category of state-sponsored cyber warfare. While their public-facing persona is that of hacktivists, their targeting, coordination, and objectives align with the strategic interests of the Iranian government, particularly in retaliating against Israeli and US interests.

According to analysis from firms like [Mandiant](https://www.mandiant.com/resources/blog/iranian-threat-actor-apt42), Iranian threat actors are known for blending disruptive attacks with intelligence gathering. While the CyberAv3ngers' actions against water utilities appear purely disruptive, they are part of a broader portfolio of Iranian cyber operations. These operations often leverage known vulnerabilities, such as the infamous [Log4Shell (CVE-2021-44228)](https://www.cisa.gov/known-exploited-vulnerabilities-catalog), rather than investing in expensive, custom-built exploits.

Why does this keep happening? Because it works. For the IRGC, this is an asymmetric victory. For the cost of a few internet scans, they can create headlines, sow fear, and demonstrate capability, forcing a superpower to expend significant resources to secure thousands of disparate, underfunded local utilities. The low technical barrier to entry for these Iranian cyberattacks on US water utilities means they are easily repeatable and scalable.


![A network diagram illustrating how to mitigate Iranian cyberattacks on US water utilities by removing PLCs from direct internet exposure.](/images/iranian-linked-cyberattacks-targeting-us-water-visual-2.png)
*Proper network segmentation and access control are the fundamental defenses against the direct exposure of critical OT assets.*


## Systemic Failures: Why Water Utilities are Low-Hanging Fruit

The core issue is not the sophistication of the attackers but the fragility of the target. America's 50,000+ drinking water systems are a patchwork of public and private entities, many of which are small municipalities with minimal IT staff and even less cybersecurity budget.

These organizations often rely on external integrators to set up their OT systems. These integrators may prioritize ease of remote access for maintenance over security, leaving ports open and default credentials in place. The result is a critical sector where devices controlling the physical world are left as exposed as a misconfigured home router. If you were the CISO here, you would have seen inbound scans from known malicious IP blocks hitting port 502 for weeks, a clear indicator of targeting that was likely missed.

> ⚠️ BreachModal Insight: The reliance on default passwords in OT environments is a form of gross negligence. This is not a 'security incident'; it is a predictable failure of basic asset management and access control. Organizations that fail to change default credentials on critical systems are choosing operational convenience over public safety.

The EPA has attempted to mandate cybersecurity standards for water systems, but these efforts have faced legal and political challenges. Until cybersecurity is treated as a non-negotiable component of operational safety, on par with water purification standards, these Iranian cyberattacks on US water utilities will continue.

## Proof of Concept: Discovering Exposed PLCs

This proof of concept demonstrates the initial reconnaissance phase used by threat actors to identify vulnerable, internet-exposed Unitronics PLCs. It uses publicly available tools to simulate the discovery process. This is for educational purposes to highlight the simplicity of the initial attack vector.

1.  **Reconnaissance with Shodan:** The first step is to use a search engine for internet-connected devices, like Shodan, to find potentially vulnerable systems. Attackers use specific queries to filter for Unitronics devices.

    ```bash
    # This Shodan query searches for web servers that identify as Unitronics devices.
    shodan search http.title:"Unitronics" http.component:"SCADA"
    ```

2.  **Port Scanning Identified Targets:** Once a potential target IP address is identified, an attacker will probe it for open OT-related ports using a tool like Nmap. This confirms the presence of services used by PLCs.

    ```bash
    # Scan a target IP for common PLC and HMI ports.
    # Port 20256 is the default for Unitronics PCOM.
    # Port 502 is Modbus, 44818 is EtherNet/IP.
    nmap -p 20256,502,44818,80,443 <TARGET_IP>
    ```

3.  **Attempting Default Login (Simulated):** The final step in gaining access is to attempt a connection using default credentials. For Unitronics, the default password is often '1111'. An attacker would use the vendor's software or a custom script to attempt this login over the identified open port (e.g., 20256).

    ```python
    # PSEUDO-CODE: This illustrates the logic, not a functional exploit.
    import socket

    target_ip = "<TARGET_IP>"
    target_port = 20256
    default_password = "1111"

    try:
        # Attempt to connect and authenticate
        plc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        plc_socket.connect((target_ip, target_port))
        # In a real scenario, a specific PCOM protocol handshake would occur here.
        # send_authentication_request(plc_socket, user="admin", password=default_password)
        print(f"[+] Success: Connection to {target_ip} on port {target_port} established. Default credentials may be valid.")
        plc_socket.close()
    except Exception as e:
        print(f"[-] Failed to connect: {e}")
    ```

4.  **Impact:** Upon successful authentication, the attacker has the same level of control as a legitimate operator. They can start and stop processes, alter logic, and lock out real users, directly impacting the physical world.

## FINAL VERDICT

The wave of **Iranian cyberattacks on US water utilities** is a direct consequence of systemic neglect. The primary risk is not data loss but physical disruption to critical life-sustaining services, and the entities bearing this risk are local communities served by under-resourced utility operators. This will not be solved by issuing another advisory. What must change is a shift from voluntary guidance to mandated, funded, and enforced cybersecurity standards for all critical infrastructure, treating secure-by-design principles as a non-negotiable requirement for any system connected to the nation's water supply.

Your OT network is now part of the global battlefield. If you're not prepared to defend it, contact BreachModal for an urgent [Operational Technology Security Assessment](https://breachmodal.com/services/ot-security). 
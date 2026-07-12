---
title: "CI/CDrone Strike: Abusing GitHub Actions to Steal Secrets"
description: "BreachModal exposes CI/CDrone Strike, a critical class of GitHub Actions vulnerabilities enabling secret exfiltration and supply chain attacks. Learn how to defend against 'Cordyceps' and 'Megalodon' campaigns."
date: 2026-07-12T17:15:08Z
slug: "ci-cdrone-strike-abusing-github-actions-to-steal"
tags: ["GitHub Actions security", "CI/CD security", "supply chain attack", "secret exfiltration", "workflow vulnerabilities", "production secrets", "pipeline security"]
author: "BreachModal Intelligence"
image: "/images/ci-cdrone-strike-abusing-github-actions-to-steal.png"
---

**The integrity of modern software supply chains is under direct siege, with GitHub Actions serving as an increasingly exploited vector for production secret exfiltration and widespread compromise.** This systemic vulnerability, often dubbed 'CI/CDrone Strike' or 'Cordyceps,' leverages the inherent trust models of CI/CD pipelines to allow threat actors to execute arbitrary code within privileged environments, pilfering critical credentials and injecting malicious payloads. Evidence from campaigns like 'Megalodon' and the compromise of widely used actions such as `tj-actions/changed-files` confirms that this isn't an isolated flaw but a pervasive class of misconfigurations. While no single CVE encapsulates this broad attack pattern, its impact has been demonstrated across high-profile targets including Microsoft, Google, and Coinbase, as reported by researchers at Novee Security and Snyk. These attacks exploit how `pull_request_target` and `workflow_run` triggers process untrusted input with elevated permissions, a critical design shortcoming in many CI/CD implementations. The consequences are direct: compromised build systems, backdoor injections, and direct access to production environments. Organizations failing to properly configure their GitHub Actions are effectively handing over the keys to their digital kingdom. One might even dryly observe that if software supply chain security were a game of chess, many organizations have already allowed their queen to be captured by a pawn that wasn't even on the board initially. 

Note what this means: The default assumptions of CI/CD platforms, particularly GitHub Actions, create a dangerous trust boundary. When a workflow processes external, untrusted input (like a pull request title or body) using a highly privileged token, it creates a direct conduit for arbitrary code execution. This systemic flaw is not a bug in GitHub's core infrastructure but a vulnerability in how organizations *implement* their workflows, often driven by convenience over security. Why does this keep happening? Because the complexity of secure pipeline configuration often outstrips the development team's security expertise, leading to critical gaps that adversaries are quick to identify and weaponize.

## The Anatomy of a CI/CDrone Strike: How GitHub Actions Become Weapons

CI/CDrone Strike fundamentally exploits the trust model of GitHub Actions, specifically how workflows triggered by `pull_request_target` and `workflow_run` operate. Unlike a standard `pull_request` trigger, which runs in a sandboxed, untrusted context with a read-only `GITHUB_TOKEN`, `pull_request_target` executes in the context of the *base repository*. This means it has access to repository secrets and a write-enabled `GITHUB_TOKEN`, even when processing attacker-controlled content from a pull request. This critical distinction is the foundation for secret exfiltration and supply chain compromise.

Attackers, often requiring only a free GitHub account, initiate a pull request containing carefully crafted malicious input. This input could be embedded in the pull request title, body, comments, or even within the source code of the pull request itself. If the `pull_request_target` workflow then interpolates this untrusted input directly into a shell command or a script (e.g., using `actions/github-script`), the attacker's code executes with the full privileges of the workflow. This bypasses typical access controls because the execution environment *believes* it is running trusted code from the repository owner.

> ⚠️ BreachModal Insight: The core issue is a misaligned trust boundary. The pipeline trusts the *event trigger* (a PR) more than it distrusts the *content* of that event, especially when using triggers that grant elevated permissions.


![CI/CDrone Strike attack flow diagram showing a malicious pull request leading to secret exfiltration via a vulnerable GitHub Actions workflow.](/images/ci-cdrone-strike-abusing-github-actions-to-steal-visual-1.png)
*Figure 1: The CI/CDrone Strike attack chain, illustrating how a malicious pull request exploits misconfigured GitHub Actions to exfiltrate sensitive data. This diagram highlights the critical points of compromise within the CI/CD pipeline.*


*Caption: An attack flow diagram illustrating the CI/CDrone Strike, showing how a malicious pull request exploits a misconfigured GitHub Actions workflow to achieve secret exfiltration and code execution. The diagram highlights the `pull_request_target` trigger as a key vulnerability point, leading to unauthorized access to repository secrets. The flow depicts initial access via pull request, command injection in a vulnerable workflow, and subsequent exfiltration of sensitive data.* 

## High-Profile CI/CDrone Strikes: A Pattern of Compromise

The threat is not theoretical; it has manifested in several significant incidents, demonstrating the scale and impact of CI/CDrone Strike. These are not isolated events but part of a discernible pattern of CI/CD pipeline attacks.

**`tj-actions/changed-files` Compromise (March 2025):** This incident saw attackers compromise the widely used `tj-actions/changed-files` GitHub action, affecting over 23,000 repositories. The attackers injected a payload designed to dump the CI/CD runner's memory, exposing sensitive environment variables and secrets to workflow logs. The attack, which began in November 2024 and initially targeted Coinbase, was achieved by pushing a malicious commit using a previously obtained GitHub token with write permissions, then modifying past release tags to evade detection, rather than altering the visible source code. This allowed the malicious code to be executed by downstream users who had pinned to a compromised tag.

**`spotbugs/sonar-findbugs` and `spotbugs/spotbugs` Exploitation (December 2024):** An attacker submitted a malicious pull request to `spotbugs/sonar-findbugs`, exploiting a `pull_request_target` workflow. This allowed them to modify the `mvnw` file, a common build wrapper. Separately, a malicious workflow was pushed to `spotbugs/spotbugs` to leak all repository secrets, including a Personal Access Token (PAT) with access to both `spotbugs/spotbugs` and `reviewdog/action-setup`. This demonstrates cross-project impact from a single initial compromise.

**`aquasecurity/trivy-action` Hijacking (March 2026):** Attackers hijacked version tags in `aquasecurity/trivy-action`, a popular container security scanner. By redirecting downstream workflows to attacker-controlled code, they were able to harvest cloud credentials from organizations relying on the action. This type of supply chain compromise leverages the implicit trust users place in versioned actions.

**Cordyceps Campaign (June 2026):** Researchers at Novee Security disclosed the 
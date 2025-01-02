import os
import requests
import base64
import time
import sys

class GitHubAnalyzer:
    def __init__(self, token, repo_name):
        self.token = token
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_name}"
        self.headers = {'Authorization': f'token {token}'}

    def fetch_data(self, url):
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    def check_documentation(self):
        url = f"{self.base_url}/readme"
        try:
            response = self.fetch_data(url)
            readme = base64.b64decode(response['content']).decode('utf-8')
            essential_sections = ['installation', 'usage', 'contributing', 'license', 'changelog']
            missing_sections = [section for section in essential_sections if section not in readme.lower()]
            if not missing_sections:
                return "README.md is present and contains all essential sections."
            else:
                return f"README.md is present but missing sections: {', '.join(missing_sections)}."
        except requests.exceptions.HTTPError:
            return "README.md file is missing."

    def analyze_issues(self):
        url = f"{self.base_url}/issues?state=open"
        open_issues = self.fetch_data(url)
        unresolved_issues = []
        for issue in open_issues:
            comments_url = issue['comments_url']
            comments = self.fetch_data(comments_url)
            resolved = any('resolved' in comment['body'].lower() for comment in comments)
            if not resolved:
                unresolved_issues.append(issue)
        inactive_issues = [issue for issue in unresolved_issues if (issue['updated_at'] < issue['created_at'])]
        if not unresolved_issues:
            return "No unresolved open issues."
        elif inactive_issues:
            return f"Found {len(unresolved_issues)} unresolved open issues, including {len(inactive_issues)} with long inactivity."
        else:
            return f"Found {len(unresolved_issues)} unresolved open issues."

    def analyze_pull_requests(self):
        url = f"{self.base_url}/pulls?state=open"
        open_pulls = self.fetch_data(url)
        unmerged_pulls = []
        for pull in open_pulls:
            if pull['merged_at']:
                continue  # Skip merged pull requests
            comments_url = pull['_links']['comments']['href']
            comments = self.fetch_data(comments_url)
            addressed = any('addressed' in comment['body'].lower() for comment in comments)
            if not addressed:
                unmerged_pulls.append(pull)
        if not unmerged_pulls:
            return "No unresolved open pull requests."
        else:
            return f"Found {len(unmerged_pulls)} unresolved open pull requests."

    def check_dependencies(self):
        manifest_files = ['package.json', 'requirements.txt']
        dependencies_status = []
        for file_name in manifest_files:
            url = f"{self.base_url}/contents/{file_name}"
            try:
                response = self.fetch_data(url)
                dependencies_status.append(f"{file_name} found and needs further analysis.")
                # Further analysis could include checking for outdated packages
            except requests.exceptions.HTTPError:
                dependencies_status.append(f"{file_name} is missing.")
        return dependencies_status

    def check_security(self):
        url = f"{self.base_url}/vulnerability-alerts"
        try:
            alerts = self.fetch_data(url)
            if alerts['total_count'] == 0:
                return "No reported vulnerabilities."
            else:
                return f"Found {alerts['total_count']} security vulnerabilities."
        except requests.exceptions.HTTPError:
            return "Could not retrieve security vulnerabilities."

    def check_license(self):
        url = f"{self.base_url}/license"
        try:
            response = self.fetch_data(url)
            if response['license']:
                return f"License file is present with {response['license']['name']} license."
            else:
                return "License file is missing."
        except requests.exceptions.HTTPError:
            return "License file is missing."

    def check_contributing_guidelines(self):
        url = f"{self.base_url}/contents/CONTRIBUTING.md"
        try:
            self.fetch_data(url)
            return "Contributing guidelines are present."
        except requests.exceptions.HTTPError:
            return "Contributing guidelines are missing."

    def check_issue_templates(self):
        url = f"{self.base_url}/contents/.github/ISSUE_TEMPLATE/"
        try:
            self.fetch_data(url)
            return "Issue templates are present."
        except requests.exceptions.HTTPError:
            return "Issue templates are missing."

    def check_pull_request_templates(self):
        url = f"{self.base_url}/contents/.github/PULL_REQUEST_TEMPLATE.md"
        try:
            self.fetch_data(url)
            return "Pull request templates are present."
        except requests.exceptions.HTTPError:
            return "Pull request templates are missing."

    def check_changelog(self):
        url = f"{self.base_url}/contents/CHANGELOG.md"
        try:
            self.fetch_data(url)
            return "Changelog is present."
        except requests.exceptions.HTTPError:
            return "Changelog is missing."

    def report_findings(self):
        documentation_status = self.check_documentation()
        issues_status = self.analyze_issues()
        pulls_status = self.analyze_pull_requests()
        dependencies_status = self.check_dependencies()
        security_status = self.check_security()
        license_status = self.check_license()
        contributing_status = self.check_contributing_guidelines()
        issue_templates_status = self.check_issue_templates()
        pr_templates_status = self.check_pull_request_templates()
        changelog_status = self.check_changelog()

        report = f"""
        Repository Analysis Report for {self.repo_name}:
        1. Documentation: {documentation_status}
        2. Open Issues: {issues_status}
        3. Open Pull Requests: {pulls_status}
        4. Dependencies Status: {', '.join(dependencies_status)}
        5. Security Status: {security_status}
        6. License: {license_status}
        7. Contributing Guidelines: {contributing_status}
        8. Issue Templates: {issue_templates_status}
        9. Pull Request Templates: {pr_templates_status}
        10. Changelog: {changelog_status}
        """
        print(report)

        # Create issues for critical problems
        if 'missing' in documentation_status.lower():
            self.create_issue('Missing README.md or essential sections', documentation_status)
        if 'long inactivity' in issues_status.lower():
            self.create_issue('Unresolved issues with long inactivity', issues_status)
        if any('missing' in status.lower() for status in dependencies_status):
            self.create_issue('Missing dependency files', ', '.join(dependencies_status))
        if 'security vulnerabilities' in security_status.lower():
            self.create_issue('Security vulnerabilities detected', security_status)
        if 'missing' in license_status.lower():
            self.create_issue('License file missing', license_status)
        if 'missing' in contributing_status.lower():
            self.create_issue('Contributing guidelines missing', contributing_status)
        if 'missing' in issue_templates_status.lower():
            self.create_issue('Issue templates missing', issue_templates_status)
        if 'missing' in pr_templates_status.lower():
            self.create_issue('Pull request templates missing', pr_templates_status)
        if 'missing' in changelog_status.lower():
            self.create_issue('Changelog missing', changelog_status)

    def create_issue(self, title, body):
        url = f"{self.base_url}/issues"
        issue = {
            'title': title,
            'body': body
        }
        self.headers.update({'Accept': 'application/vnd.github.v3+json'})
        response = requests.post(url, json=issue, headers=self.headers)
        if response.status_code == 201:
            print(f"Issue created: {title}")
        else:
            print(f"Failed to create issue: {response.content}")

if __name__ == '__main__':
    print("""
    ░▒▓███████▓▒░░▒▓████████▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░        ░▒▓███████▓▒░▒▓███████▓▒░░▒▓████████▓▒░▒▓██████▓▒░▒▓████████▓▒░▒▓██████▓▒░░▒▓███████▓▒░  
    ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░     ░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░  ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
    ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░     ░▒▓█▓▒░        ░▒▓█▓▒░  ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
    ░▒▓███████▓▒░░▒▓██████▓▒░ ░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░       ░▒▓██████▓▒░░▒▓███████▓▒░░▒▓██████▓▒░░▒▓█▓▒░        ░▒▓█▓▒░  ░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░  
    ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░             ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░     ░▒▓█▓▒░        ░▒▓█▓▒░  ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
    ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░             ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░     ░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░  ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
    ░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓█▓▒░       ░▒▓██████▓▒░       ░▒▓███████▓▒░░▒▓█▓▒░      ░▒▓████████▓▒░▒▓██████▓▒░  ░▒▓█▓▒░   ░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░  
                                                                                       __            ___ _   _________  ____  
                                                                                      / /  __ __    / _ | | / /  _/ _ \/_  /  
                                                                                     / _ \/ // /   / __ | |/ // // // / / /_  
                                                                                    /_.__/\_, /   /_/ |_|___/___/____/ /___/  
                                                                                        /___/  

           https://github.com/avidzcheetah  
""")

    token = input("Enter your GitHub token: ")
    repo_name = input("Enter the repository name (username/repo): ")
    
    print("Analyzing", end="")
    for _ in range(3):
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(1.0)
    print()  # Newline after animation

    analyzer = GitHubAnalyzer(token, repo_name)
    analyzer.report_findings()

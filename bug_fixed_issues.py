"""Get list of merged PRs and plots time to merge."""
# noqa: D103

import json
from pathlib import Path
from warnings import warn

import pandas as pd
import plotly.express as px
import requests
from rich import print

USERNAME = "Remi-Gau"

# may require a token if run often
TOKEN_FILE = Path(__file__).parent / ("token.txt")
TOKEN_FILE = Path("/home/remi/Documents/tokens/gh_read_repo.txt")

# repo to check
GH_USERNAME = "nilearn"
GH_REPO = "nilearn"

DEBUG = False

exclude_users = [
]

# Set to true to rely on presaved list of PRs or issues
USE_LOCAL = False


def root_folder():
    """Get the root folder of the repo."""
    return Path(__file__).parent


def get_list_of_closed_issues(gh_username: str, gh_repo: str, auth=None):
    """List open PRs for a given repo.

    Parameters
    ----------
    gh_username : str
        _description_
    gh_repo : str
        _description_
    auth : None | tuple[str, str], optional
        _description_, by default None

    Returns
    -------
    _type_
        _description_
    """
    closed_prs = []
    base_url = "https://api.github.com/repos/"
    url = f"{base_url}{gh_username}/{gh_repo}/issues?per_page=100&state=closed&page="
    for page in range(1, 200):
        url_page = f"{url}{page}"
        print(f"Getting page {page} of issues")
        response = requests.get(f"{url_page}", auth=auth)
        if DEBUG and page > 1:
            break
        if response.status_code != 200:
            warn(f"Error {response.status_code}: {response.text}")
            break
        closed_prs.extend(response.json())
    return closed_prs


def main():
    """Get PRs, save their diffs to files and list all files touched by PRs."""

    output_file = root_folder() / f"closed_issues_{GH_USERNAME}_{GH_REPO}"

    TOKEN = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            TOKEN = f.read().strip()

    auth = None if USERNAME is None or TOKEN is None else (USERNAME, TOKEN)

    if not USE_LOCAL:
        issues = get_list_of_closed_issues(
            gh_username=GH_USERNAME, gh_repo=GH_REPO, auth=auth
        )
        with open(output_file.with_suffix(".json"), "w") as f:
            json.dump(issues, f, indent=2)
    else:
        with open(output_file.with_suffix(".json")) as f:
            issues = json.load(f)

    data = {
        "number": [],
        "created_at": [],
        "closed_at": [],
        "state": [],
        "title": [],
        "user": [],
    }
    for issue_ in issues:
        labels = [x["name"] for x in issue_["labels"]]
        if issue_["closed_at"] and 'Bug' in labels:
            data["number"].append(issue_["number"])
            data["created_at"].append(issue_["created_at"])
            data["closed_at"].append(issue_["closed_at"])
            data["state"].append(issue_["state"])
            data["title"].append(issue_["title"])
            data["user"].append(issue_["user"]["login"])    

    df = pd.DataFrame(data)

    df["created_at"] = pd.to_datetime(df["created_at"])
    df["closed_at"] = pd.to_datetime(df["closed_at"])
    df["time_to_fix"] = (df["closed_at"] - df["created_at"]).dt.days

    # threshold time_to_fix to X days
    df.loc[df["time_to_fix"] >= 180, "time_to_fix"] = 180    

    df.to_csv(output_file.with_suffix(".tsv"), index=False, sep="\t")

    # use plotly to plot histogram of time to merge on a logaithmic scale
    fig = px.histogram(
        df,
        x="time_to_fix",
        nbins=90,
        range_x=[0, 180],
        title="Time to fix bug (days)",
    )
    fig.write_html(output_file.with_suffix(".html"))
    fig.show()    

if __name__ == "__main__":
    main()

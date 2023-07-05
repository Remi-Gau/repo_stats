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
TOKEN_FILE = Path(__file__).parent.joinpath("token.txt")

# repo to check
GH_USERNAME = "nilearn"
GH_REPO = "nilearn"

DEBUG = False

exclude_users = [
    "dependabot[bot]",
    "pre-commit-ci[bot]",
    "allcontributors[bot]",
    "github-actions[bot]",
]

CORE_DEVS = [
    "GaelVaroquaux",
    "alexisthual",
    "bthirion",
    "emdupre",
    "htwangtw",
    "jeromedockes",
    "Nicolas Gensollen",
    "Remi-Gau",
    "tsalo",
    "ymzayek",
    "AlexandreAbraham",
    "KamalakerDadi",
    "lesteve",
    "pgervais",
    "kchawla-pi",
]


# Set to true to rely on presaved list of PRs or issues
USE_LOCAL = True


def root_folder():
    """Get the root folder of the repo."""
    return Path(__file__).parent


def get_list_of_closed_prs(gh_username: str, gh_repo: str, auth=None):
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
    url = f"{base_url}{gh_username}/{gh_repo}/pulls?per_page=100&state=closed&page="
    for page in range(1, 100):
        url_page = f"{url}{page}"
        print(f"Getting page {page} of PRs")
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

    output_file = root_folder() / f"closed_prs_{GH_USERNAME}_{GH_REPO}"

    TOKEN = None
    if TOKEN_FILE.exists():
        with open(Path(__file__).parent / "token.txt") as f:
            TOKEN = f.read().strip()

    auth = None if USERNAME is None or TOKEN is None else (USERNAME, TOKEN)

    if not USE_LOCAL:
        pulls = get_list_of_closed_prs(
            gh_username=GH_USERNAME, gh_repo=GH_REPO, auth=auth
        )
        with open(output_file.with_suffix(".json"), "w") as f:
            json.dump(pulls, f, indent=2)
    else:
        with open(output_file.with_suffix(".json")) as f:
            pulls = json.load(f)

    data = {
        "number": [],
        "created_at": [],
        "merged_at": [],
        "state": [],
        "title": [],
        "user": [],
    }
    for pr in pulls:
        if pr["merged_at"] and pr["user"]["login"] not in exclude_users:
            data["number"].append(pr["number"])
            data["created_at"].append(pr["created_at"])
            data["merged_at"].append(pr["merged_at"])
            data["state"].append(pr["state"])
            data["title"].append(pr["title"])
            data["user"].append(pr["user"]["login"])

    df = pd.DataFrame(data)

    df["created_at"] = pd.to_datetime(df["created_at"])
    df["merged_at"] = pd.to_datetime(df["merged_at"])
    df["time_to_merge"] = (df["merged_at"] - df["created_at"]).dt.days

    # set time to merge to 180 if it is greater than 180
    df.loc[df["time_to_merge"] >= 90, "time_to_merge"] = 90

    df.to_csv(output_file.with_suffix(".tsv"), index=False, sep="\t")

    # use plotly to plot histogram of time to merge on a logaithmic scale
    fig = px.histogram(
        df,
        x="time_to_merge",
        nbins=90,
        range_x=[0, 90],
        title="Time to merge PRs (days)",
    )
    fig.write_html(output_file.with_suffix(".html"))
    fig.show()

    # remove PRs from core devs
    output_file = root_folder() / f"closed_prs_{GH_USERNAME}_{GH_REPO}_noCoreDev"
    df = df[~df["user"].isin(CORE_DEVS)]
    df.to_csv(output_file.with_suffix(".tsv"), index=False, sep="\t")
    fig = px.histogram(
        df,
        x="time_to_merge",
        nbins=90,
        range_x=[0, 90],
        title="Time to merge PRs (days) - no core devs",
    )
    fig.write_html(output_file.with_suffix(".html"))
    fig.show()

    #  show unique users
    print(sorted(df["user"].unique()))


if __name__ == "__main__":
    main()

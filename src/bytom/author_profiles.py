import logging
import re
import io
import json
import os
import dr_util.file_utils as fu
import bytom.arxiv_utils as xu

from enum import Enum
from datetime import datetime
from pathlib import Path


class SUMMARY_SOURCE(Enum):
    ABSTRACT = 1
    # NO_APPENDIX = 2
    # FULL_PDF = 3


class SUMMARY_FORMAT(Enum):
    MARKDOWN = 1
    # JSON = 2

# --- Create bio data json--- #

def save_info_json(
    cfg, names_info
):
    # Convert to JSON
    json_output = json.dumps(names_info, indent=4)

    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(f"{cfg.author_info_file}"), exist_ok=True)

    # Save to a file
    with open(f"{cfg.author_info_file}", 'w') as json_file:
        json.dump(names_info, json_file, indent=4)

# --- Info Gathering Functions --- #


def get_author_papers(author, kwargs={}):
    logging.info(f">> Getting papers from arxiv api for author: {author}")
    # First get all the recent papers by this author, ordered by date
    query = xu.build_author_query(author, kwargs=kwargs)
    entries = xu.query_api(query)

    logging.info(f">> Total number papers: {len(entries)}")
    structured_responses = [xu.parse_paper_entry(pent) for pent in entries]
    return structured_responses


# --- Data Inspect Functions --- #


def list_authors_with_summaries(cfg, version=None):
    if version is not None:
        assert False, "version specification isn't defined  yet"

    profs = set()
    author_data_path = Path(cfg.author_summaries_dir)
    for fn in author_data_path.iterdir():
        rmatch = re.match(cfg.author_summary_file_pattern, fn.stem)
        profs.add(rmatch.group("professor_name").replace("_", " ").title())
    return list(profs)


# --- Profile Writing Functions --- #


def format_response_abstract_to_markdown(response):
    buff = io.StringIO()

    buff.write(f"### **Title:** {response['title']}\n\n")
    buff.write(f"**Publish Date:** {response['published']}\n\n")
    buff.write(f"**First Author:** {response['authors'][0]}\n\n")
    buff.write(f"**Last Author:** {response['authors'][-1]}\n\n")
    if len(response["authors"]) > 2:
        buff.write(f"**Middle Authors:** {', '.join(response['authors'][1:-1])}\n\n")
    buff.write(f"**Abstract:** {response['abstract']}\n\n")
    buff.write(f'{"-"*15}\n\n\n')
    return buff.getvalue()


def make_author_page(
    cfg,
    author,
    responses=None,
    author_info=None,
    max_papers=100,
    max_years=20,
    first_last_only=False,
):
    if author_info is None:
        author_infos = fu.load_file(cfg.author_info_file)
        author_info = author_infos[author]

    if first_last_only:
        if responses is None:
            responses = get_author_papers(
                author, kwargs={"max_results": max_papers * 5}
            )
        responses = [
            r for r in responses if author in [r["authors"][0], r["authors"][-1]]
        ]
    elif responses is None:
        responses = get_author_papers(author, kwargs={"max_results": max_papers})
    responses = responses[:max_papers]

    buff = io.StringIO()
    buff.write(f"# Research Summary for **{author}**\n\n")
    buff.write(f"## {author} Bio\n\n")
    buff.write(f"{author_info}\n\n")

    buff.write("## Recent Papers\n\n")
    for resp in responses:
        published = datetime.strptime(resp["published"], "%Y-%m-%d")
        if (datetime.now() - published).days / 365.25 < max_years:
            buff.write(format_response_abstract_to_markdown(resp))
    return buff.getvalue()


def write_author_page(
    cfg,
    author,
    version,
    responses=None,
    author_info=None,
    max_papers=100,
    max_years=20,
    first_last_only=False,
):
    author_page = make_author_page(
        cfg,
        author,
        responses=responses,
        author_info=author_info,
        max_papers=max_papers,
        max_years=max_years,
        first_last_only=first_last_only,
    )
    author_str = author.lower().replace(" ", "_")
    fl_only = ".flonly" if first_last_only else ""
    os.makedirs(os.path.dirname(f"{cfg.author_summaries_dir}"), exist_ok=True)

    fu.dump_file(
        author_page,
        f"{cfg.author_summaries_dir}{author_str}.markdown."
        f"v{version}.maxp{max_papers}.maxy{max_years}{fl_only}.txt",
    )

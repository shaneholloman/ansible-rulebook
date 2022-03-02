import durable.lang
import multiprocessing as mp

from typing import Dict, List
import ansible_runner
import shutil
import tempfile
import os
import yaml
import glob
import json
import dpath.util
from pprint import pprint
from .util import get_horizontal_rule

from typing import Optional


def none(inventory: Dict, hosts: List, variables: Dict, facts: Dict, ruleset: str):
    pass


def debug(**kwargs):
    print(get_horizontal_rule("="))
    pprint(durable.lang.get_facts(kwargs["ruleset"]))
    print(get_horizontal_rule("="))
    pprint(kwargs)
    print(get_horizontal_rule("="))


def print_event(
    inventory: Dict,
    hosts: List,
    variables: Dict,
    facts: Dict,
    ruleset: str,
    glob: Optional[str] = None,
    pretty: Optional[str] = None,
):
    print_fn = print
    if pretty:
        print_fn = pprint
    if glob:
        print_fn(dpath.util.get(variables["event"], glob, separator="."))
    else:
        print_fn(variables["event"])


def assert_fact(
    inventory: Dict, hosts: List, variables: Dict, facts: Dict, ruleset: str, fact: Dict
):
    durable.lang.assert_fact(ruleset, fact)


def retract_fact(
    inventory: Dict, hosts: List, variables: Dict, facts: Dict, ruleset: str, fact: Dict
):
    durable.lang.retract_fact(ruleset, fact)


def post_event(
    inventory: Dict, hosts: List, variables: Dict, facts: Dict, ruleset: str, fact: Dict
):
    durable.lang.post(ruleset, fact)


def run_playbook(
    inventory: Dict,
    hosts: List,
    variables: Dict,
    facts: Dict,
    ruleset: str,
    name: str,
    assert_facts: Optional[bool] = None,
    post_events: Optional[bool] = None,
    verbosity: int = 0,
    **kwargs,
):
    logger = mp.get_logger()

    temp = tempfile.mkdtemp(prefix="run_playbook")
    logger.debug(f"temp {temp}")
    logger.debug(f"variables {variables}")
    logger.debug(f"facts {facts}")

    variables["facts"] = facts

    os.mkdir(os.path.join(temp, "env"))
    with open(os.path.join(temp, "env", "extravars"), "w") as f:
        f.write(yaml.dump(variables))
    os.mkdir(os.path.join(temp, "inventory"))
    with open(os.path.join(temp, "inventory", "hosts"), "w") as f:
        f.write(yaml.dump(inventory))
    os.mkdir(os.path.join(temp, "project"))

    shutil.copy(name, os.path.join(temp, "project", name))

    host_limit = ",".join(hosts)

    ansible_runner.run(
        playbook=name, private_data_dir=temp, limit=host_limit, verbosity=verbosity
    )

    if assert_facts or post_events:
        logger.debug('assert_facts')
        for host_facts in glob.glob(
            os.path.join(temp, "artifacts", "*", "fact_cache", "*")
        ):
            with open(host_facts) as f:
                fact = json.loads(f.read())
            logger.debug(f'fact {fact}')
            durable.lang.assert_fact(ruleset, fact)
            if post_events:
                durable.lang.retract_fact(ruleset, fact)


actions = dict(
    none=none,
    debug=debug,
    print_event=print_event,
    assert_fact=assert_fact,
    retract_fact=retract_fact,
    post_event=post_event,
    run_playbook=run_playbook,
)

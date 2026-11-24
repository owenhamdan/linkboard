"""Checks that system.yaml matches the code, beyond what the JSON Schema can check.

1. Every environment variable a service reads is listed in system.yaml, and nothing else.
2. Every endpoint a service calls exists in the called service's openapi.yaml.
3. Every path system.yaml points to exists.
"""
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_READ = re.compile(r"""os\.environ(?:\.get)?[\(\[]\s*["']([A-Z][A-Z0-9_]*)["']""")


def env_read_by(path):
    names = set()
    for name in os.listdir(path):
        if name.endswith(".py"):
            with open(os.path.join(path, name)) as f:
                names |= set(ENV_READ.findall(f.read()))
    return names


def main():
    with open(os.path.join(ROOT, "system.yaml")) as f:
        system = yaml.safe_load(f)
    errors = []
    specs = {}
    for name, svc in system["services"].items():
        for key in ("path", "openapi", "migrations"):
            if not os.path.exists(os.path.join(ROOT, svc[key])):
                errors.append(f"{name}: {key} {svc[key]} does not exist")
        with open(os.path.join(ROOT, svc["openapi"])) as f:
            specs[name] = yaml.safe_load(f)
        in_code = env_read_by(os.path.join(ROOT, svc["path"]))
        listed = set(svc["env"])
        for var in sorted(in_code - listed):
            errors.append(f"{name}: reads {var} but system.yaml does not list it")
        for var in sorted(listed - in_code):
            errors.append(f"{name}: system.yaml lists {var} but the code never reads it")
    for name, svc in system["services"].items():
        for call in svc.get("calls", []):
            target = specs.get(call["service"])
            if target is None:
                errors.append(f"{name}: calls unknown service {call['service']}")
                continue
            for endpoint in call["endpoints"]:
                method, path = endpoint.split(" ", 1)
                if method.lower() not in target["paths"].get(path, {}):
                    errors.append(f"{name}: calls {endpoint}, missing from {call['service']}'s openapi.yaml")
            if call["url_env"] not in svc["env"]:
                errors.append(f"{name}: url_env {call['url_env']} is not in its env list")
    for err in errors:
        print("ERROR", err)
    print("system.yaml matches the code" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

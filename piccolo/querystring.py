from __future__ import annotations
from copy import copy
import datetime
from dataclasses import dataclass
from string import Formatter
import typing as t


@dataclass
class Unquoted():
    """
    Used when we want the value to be unquoted because it's a Postgres
    keyword - for example DEFAULT.
    """
    value: str


@dataclass
class Fragment():
    prefix: str
    index: int = 0
    no_arg: bool = False


class QueryString():

    def __init__(self, template: str, *args: t.Any) -> None:
        """
        Example template: "WHERE {} = {}"
        """
        self.template = template
        self.args = args

    def __str__(self):
        """
        The SQL returned by the __str__ method isn't used directly in queries
        - it's just a usability feature.
        """
        _, bundled, combined_args = self.bundle(
            start_index=1,
            bundled=[],
            combined_args=[]
        )
        template = ''.join([
            fragment.prefix + ('' if fragment.no_arg else '{}') for fragment in bundled
        ])

        # Do some basic type conversion here.
        converted_args = []
        for arg in combined_args:
            _type = type(arg)
            if _type == str:
                converted_args.append(f"'{arg}'")
            elif _type == datetime:
                dt_string = arg.isoformat().replace('T', ' ')
                converted_args.append(f"'{dt_string}'")
            elif arg == None:
                converted_args.append('null')
            else:
                converted_args.append(arg)

        return template.format(*converted_args)

    def bundle(self, start_index=1, bundled=[], combined_args=[]):
        # Split up the string, separating by {}.
        fragments = [
            Fragment(prefix=i[0]) for i in Formatter().parse(self.template)
        ]

        for index, fragment in enumerate(fragments):
            try:
                value = self.args[index]
            except IndexError:
                # trailing element
                fragment.no_arg = True
                bundled.append(fragment)
            else:
                if type(value) == self.__class__:
                    fragment.no_arg = True
                    bundled.append(fragment)

                    start_index, _, _ = value.bundle(
                        start_index=start_index,
                        bundled=bundled,
                        combined_args=combined_args,
                    )
                else:
                    fragment.index = start_index
                    bundled.append(fragment)
                    start_index += 1
                    combined_args.append(value)

        return (start_index, bundled, combined_args)

    def compile_string(self) -> t.Tuple[str, t.List[t.Any]]:
        """
        Compiles the template ready for Postgres - keeping the arguments
        separate from the template.
        """
        _, bundled, combined_args = self.bundle(
            start_index=1,
            bundled=[],
            combined_args=[]
        )
        string = ''.join([
            fragment.prefix + ('' if fragment.no_arg else f'${fragment.index}') for fragment in bundled
        ])
        return (string, combined_args)

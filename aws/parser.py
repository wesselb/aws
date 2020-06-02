import abc


class Parser:
    """Parse a string.

    Args:
        data (str): Lines to parse.
    """

    def __init__(self, data):
        self.lines = data.split('\n')

    def find_line(self, match):
        """Find the next line containing a string.

        Args:
            match (str): String to match.
        """
        while match.lower() not in self.lines[0].lower():
            self.next_line()

            if not self.lines_left():
                raise RuntimeError(f'Attempting to match "{match.lower()}", '
                                   f'but no lines left.')

    def next_line(self):
        """Go to the next line."""
        self.lines = self.lines[1:]

    def lines_left(self):
        """Check if there are any lines left.

        Returns:
            bool: `True` if any lines are left, otherwise `False`.
        """
        return len(self.lines) > 0

    def parse(self, *parts):
        """Parse the current line.

        Args:
            *parts (tuple[:class:`.parser.RegexPart`]): Parts of the line.
        """
        return Regex(*parts).parse(self.lines[0])


class Regex:
    """Regex.

    Args:
        *parts (tuple[:class:`.parser.RegexPart`]): Parts of the regex.
    """

    def __init__(self, *parts):
        self.parts = parts

    def parse(self, data):
        """Parse data according to the regex.

        Args:
            data (str): Data to parse.

        Returns:
            list: Matched results.
        """
        results = []
        for part in self.parts:
            data, results = part.parse(data, results)
        return results


class RegexPart(metaclass=abc.ABCMeta):
    """Part of a regex."""

    @abc.abstractmethod
    def parse(self, data, results):
        """Parse data and match results.

        Args:
            data (str): Data to parse.
            results (list): Matches so far.

        Returns:
            tuple[str, list]: Data left to parse and updated results.
        """


class Whitespace(RegexPart):
    """Whitespace."""

    def parse(self, data, results):
        while data[0] in {' ', '\n'}:
            data = data[1:]
        return data, results


class Float(RegexPart):
    """Floating point number."""

    def parse(self, data, results):
        num = ''
        while data[0] in {'0', '1', '2', '3', '4',
                          '5', '6', '7', '8', '9', '.', 'e', '-', '+'}:
            num += data[0]
            data = data[1:]
        return data, results + [float(num)]


class Literal(RegexPart):
    """Literal.

    Args:
        literal (str): String to match.
    """

    def __init__(self, literal):
        self.literal = literal

    def parse(self, data, results):
        i = 0
        while i < len(self.literal):
            if data[0] == self.literal[i]:
                # Match! Go on.
                i += 1
                data = data[1:]
            else:
                raise RuntimeError(f'When parsing literal "{self.literal}" at '
                                   f'position {i + 1}, expected '
                                   f'"{self.literal[i]}" but got "{data[0]}".')
        return data, results

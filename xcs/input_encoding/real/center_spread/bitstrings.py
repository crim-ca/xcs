
from typing import List, Tuple
from random import sample, random, randint, choice

from xcs.bitstrings import BitConditionBase, BitString as CoreBitString
from xcs.input_encoding.real.center_spread.util import EncoderDecoder, random_in


class BitConditionRealEncoding(BitConditionBase):
    """See Documentation of base class."""

    def _encode(self, center_spreads: List[Tuple[float, float]]) -> CoreBitString:
        result = CoreBitString('')
        for (center, spread) in center_spreads:
            result += self.real_translator.encode(center)
            result += self.real_translator.encode(spread)
        return result

    def __init__(self, encoder: EncoderDecoder, center_spreads: List[Tuple[float, float]], mutation_strength: float):
        assert len(center_spreads) > 0
        assert (mutation_strength > 0) and (mutation_strength < 1)
        self.real_translator = encoder
        self.mutation_strength = mutation_strength
        BitConditionBase.__init__(self, bits=self._encode(center_spreads), mask=None)
        self.center_spreads = center_spreads

    @classmethod
    def random(cls, encoder: EncoderDecoder, mutation_strength: float, length: int):
        return BitConditionRealEncoding.random_from_center_list(
            center_list=encoder.choice(length),
            encoder=encoder,
            mutation_strength=mutation_strength)

    @classmethod
    def random_from_center_list(cls, center_list: List[float], encoder: EncoderDecoder, mutation_strength: float):
        assert all([(center <= encoder.extremes[1]) and (center >= encoder.extremes[0]) for center in center_list])
        center_spread_list = []
        for center in center_list:
            spread = random() * min(center - encoder.extremes[0], encoder.extremes[1] - center)
            center_spread_list.append((center, spread))
        return cls(encoder=encoder, center_spreads=center_spread_list, mutation_strength=mutation_strength)

    @classmethod
    def clip_center_spread_class(cls, encoder: EncoderDecoder, center_spread: Tuple[float, float]) -> Tuple[float, float]:
        """Clips an interval in a way that it represents a valid range of values."""
        center, spread = center_spread
        center = encoder.clip(center)
        spread = min(spread, min(center - encoder.extremes[0], encoder.extremes[1] - center))
        return center, spread

    def clip_center_spread(self, center_spread: Tuple[float, float]) -> Tuple[float, float]:
        """Clips an interval in a way that it represents a valid range of values."""
        return BitConditionRealEncoding.clip_center_spread_class(self.real_translator, center_spread)

    def __str__(self):
        """Overloads str(condition)"""
        return ','.join(["(%.2f, %.2f)" % (center, spread) for (center, spread) in self])

    def __len__(self):
        """Overloads len(condition)"""
        return len(self.center_spreads)

    def __getitem__(self, index):
        """Overloads condition[index]. The values yielded by the index
        operator are True (1), False (0), or None (#)."""
        if isinstance(index, slice):
            return BitConditionRealEncoding(self.real_translator, self.center_spreads[index], self.mutation_strength)
            # return BitCondition(self._bits[index], self._mask[index])
        # return self._bits[index] if self._mask[index] else None
        return self.center_spreads[index]

    def __contains__(self, item):
        """Overloads 'in' operator."""
        # assert isinstance(item, Tuple[float, float])
        return item in self.center_spreads

    def __call__(self, other):
        """Overloads condition(situation). Returns a Boolean value that
        indicates whether the other value satisfies this condition."""

        assert isinstance(other, (BitString, BitConditionRealEncoding)), "Type is => " + str(type(other))
        assert len(self) == len(other)

        if isinstance(other, BitString):
            situation = other

            center_spreads = [(center, spread) for (center, spread) in self]
            values = [value for value in situation]
            return all(
                [((value >= center - spread) and (value <= center + spread))
                 for ((center, spread), value) in zip(center_spreads, values)])
        else:  # 'other' is a condition
            other_condition = other

            my_center_spreads = [(my_center, my_spread) for (my_center, my_spread) in self]
            other_center_spreads = [(other_center, other_spread) for (other_center, other_spread) in other_condition]
            return all(
                [((my_center - my_spread <= other_center - other_spread) and (my_center + my_spread >= other_center + other_spread))
                 for ((my_center, my_spread), (other_center, other_spread)) in zip(my_center_spreads, other_center_spreads)])

    def __iter__(self):
        """Overloads iter(bitstring), and also, for bit in bitstring"""
        return iter(self.center_spreads)

    def _mutate_interval_by_translation(self, interval: Tuple[float, float], value: float) -> Tuple[float, float]:
        center, spread = interval
        bottom, top = center - spread, center + spread  # interval is [bottom, top]
        # let's do a translate
        if spread == 0:
            # there is nothing else to do:
            new_center, new_spread = center, spread
        else:
            delta_min_max = (
                max(self.real_translator.extremes[0] - bottom, value - top),
                min(self.real_translator.extremes[1] - top, value - bottom))
            # let's choose a delta - preventing a 0 which won't translate anything:
            delta = random_in(delta_min_max[0], delta_min_max[1])
            while delta == 0:
                delta = random_in(delta_min_max[0], delta_min_max[1])
            new_center = center + delta
            new_spread = spread
        return new_center, new_spread

    def _mutate_interval_by_stretching(self, interval: Tuple[int, int], value: int) -> Tuple[int, int]:
        center, spread = interval
        bottom, top = center - spread, center + spread  # interval is [bottom, top]
        # let's do a shrinking\stretching of the interval
        if spread == 0 and (
                (center == self.real_translator.extremes[0]) or (center == self.real_translator.extremes[1])):
            # there is nothing else to do:
            new_center, new_spread = center, spread
        else:
            # Stretching can't make the interval too large. So:
            max_spread = min(center - self.real_translator.extremes[0], self.real_translator.extremes[1] - center)
            min_spread = abs(center - value)
            new_spread = random_in(min_spread, max_spread)
            while new_spread == spread:  # I actually want to mutate!
                new_spread = random_in(min_spread, max_spread)

            # if spread == 0:
            #     possible_spreads = list(
            #         range(min(self.real_translator.extremes[1] - value, value - self.real_translator.extremes[0])))
            # else:
            #     # Stretching can't make the interval too large. So:
            #     max_factor = (self.real_translator.extremes[1] - self.real_translator.extremes[0]) / (
            #                 top - bottom)  # max stretching
            #     max_spread = spread * self.real_translator.encode_as_int(max_factor)
            #     # min_factor = (center - value) / spread
            #     min_spread = abs(center - value)
            #     possible_spreads = list(range(min_spread, max_spread))
            #     # possible_spreads = list(range(spread * self.real_translator.encode_as_int(min_factor),
            #     #                               spread * self.real_translator.encode_as_int(max_factor)))
            # if (0 in possible_spreads) and (spread != 0):
            #     possible_spreads.remove(0)  # spread of 0 doesn't seem reasonable
            # if spread in possible_spreads:
            #     possible_spreads.remove(spread)
            # if len(possible_spreads) == 0:
            #     # no stretching possible
            #     new_spread = spread
            # else:
            #     # let's choose a delta:
            #     new_spread = choice(possible_spreads)
            new_center = center
            # print("[translate.stretch] (%d,%d) -> (%d,%d)" % (center, spread, new_center, new_spread))
        return new_center, new_spread

    def mutate(self, situation):
        center_spread_list = []
        for (center, spread), value in zip(self, situation):
            if random() < 0.5:
                new_center, new_spread = self._mutate_interval_by_translation(interval=(center, spread), value=value)
            else:
                new_center, new_spread = self._mutate_interval_by_stretching(interval=(center, spread), value=value)
            center_spread_list.append((new_center, new_spread))
        return BitConditionRealEncoding(
            encoder=self.real_translator,
            center_spreads=center_spread_list,
            mutation_strength=self.mutation_strength)

    def crossover_with(self, other, points):
        """Perform 2-point crossover on this bit condition and another of
        the same length, returning the two resulting children.

        Usage:
            offspring1, offspring2 = condition1.crossover_with(condition2)

        Arguments:
            other: A second BitCondition of the same length as this one.
            points: An int, the number of crossover points of the
                crossover operation.
        Return:
            A tuple (condition1, condition2) of BitConditions, where the
            value at each position of this BitCondition and the other is
            preserved in one or the other of the two resulting conditions.
        """
        assert isinstance(other, BitConditionRealEncoding)
        assert len(self) == len(other)
        assert points < len(self)

        if self == other:
            # nothing to do
            print(" CROSSOVER =====> ARE THE SAME????????????????????????")  # TODO: take this out.
            return self, other
        else:
            print(" CROSSOVER =====> not the same")
            pts = [-1] + sample(range(len(self) - 2), points) + [len(self) - 1]
            pts.sort()
            pts = list(map(lambda x: x + 1, pts))
            genome_1, genome_2 = self, other
            result = ([], [])
            for begin, end in zip(pts[:-1], pts[1:]):
                result = (result[0] + genome_1.center_spreads[begin: end], result[1] + genome_2.center_spreads[begin: end])
                genome_1, genome_2 = (self, other) if genome_1 == other else (other, self)
            return \
                BitConditionRealEncoding(self.real_translator, result[0], self.mutation_strength), \
                BitConditionRealEncoding(self.real_translator, result[1], self.mutation_strength)


class BitString(CoreBitString):

    def __init__(self, encoder: EncoderDecoder, reals: List[float]):
        assert len(reals) > 0
        self.as_reals = reals
        as_bitstring = CoreBitString('')
        for a_real in reals:
            as_bitstring += encoder.encode(a_real)
        CoreBitString.__init__(self, bits=as_bitstring)
        self.real_translator = encoder

    @classmethod
    def random_from(cls, encoder: EncoderDecoder, length):
        assert isinstance(length, int) and length >= 0
        return cls(encoder=encoder, reals=encoder.choice(length))

    def __len__(self):
        """Overloads len(instance)"""
        return len(self.as_reals)

    def __iter__(self):
        """Overloads iter(bitstring), and also, for bit in bitstring"""
        return iter(self.as_reals)

    def __str__(self):
        """Overloads str(bitstring)"""
        return ','.join(["%.2f" % (value) for value in self])

    def cover(self):
        """Create a new bit condition that matches the provided bit string,
        with the indicated per-index wildcard probability.

        Usage:
            condition = BitCondition.cover(bitstring, .33)
            assert condition(bitstring)

        Arguments:
            bits: A BitString which the resulting condition must match.
            wildcard_probability: A float in the range [0, 1] which
            indicates the likelihood of any given bit position containing
            a wildcard.
        Return:
            A randomly generated BitCondition which matches the given bits.
        """
        return BitConditionRealEncoding.random_from_center_list(
            center_list=[value for value in self],
            encoder=self.real_translator,
            mutation_strength=0.1)  # TODO: value of mutation strenght!!!!!

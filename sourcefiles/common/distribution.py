'''
Implement Distribution objects.

A Distributuion is just a collection of (weight, value_list) pairs.
When generating a random item from the distribution, pick a pair based on
the weights, then return a random element of the pair's value_list.
'''

from __future__ import annotations

from common.random import RNGType
import random
import typing


T = typing.TypeVar('T')
ObjType = typing.Union[T, typing.Sequence[T]]


class ZeroWeightException(ValueError):
    '''Raised when an entry in a distributuion is given zero weight.'''


class Distribution(typing.Generic[T]):
    '''
    This class allows the user to define relative frequencies of objects and
    generate random objects according to that distribution.  If the object
    given is a sequence, then the behavior is to give a random item from the
    sequence.
    '''
    def __init__(self, *weight_object_pairs: typing.Tuple[int, ObjType]):
        '''
        Define the initial weight/object pairs for the distributuion

        Example:
        dist = Distributution(
            (5, range(0, 10, 2),
            (10, range(1, 10, 2)
        )
        This defines a distribution that choose uniformly from (0, 2, 4, 8)
        one third of the time and will choose uniformly from (1, 3, 5, 9) the
        other two thirds of the time.
        '''

        self.__total_weight = 0
        self.weight_object_pairs: list[typing.Tuple[int, ObjType]] = []

        new_pairs = self._handle_weight_object_pairs(weight_object_pairs)
        self.set_weight_object_pairs(new_pairs)

    @staticmethod
    def _handle_weight_object_pairs(
            weight_object_pairs: typing.Sequence[typing.Tuple[int, ObjType]]
    ) -> list[typing.Tuple[int, ObjType]]:
        '''
        Replace non-sequences with a one element list so that random.choice()
        can be used.
        '''
        new_pairs = list(weight_object_pairs)
        for ind, pair in enumerate(new_pairs):
            weight, obj = pair

            if weight == 0:
                raise ZeroWeightException(
                    f'Entry ({weight}, {obj}) has zero weight.'
                )

            if not isinstance(obj, typing.Sequence):
                new_pairs[ind] = (weight, [obj])

        return new_pairs

    def get_total_weight(self) -> int:
        '''
        Return the total weight that the distribution has.
        '''
        return self.__total_weight

    def get_random_item(self, rng: RNGType) -> T:
        '''
        Get a random item from the distributuion.
        First choose a weight-object pair based on weights.  Then (uniformly)
        choose an element of that object.
        '''
        target = rng.randrange(0, self.__total_weight)

        cum_weight = 0
        for weight, obj in self.weight_object_pairs:
            cum_weight += weight

            if cum_weight > target:
                return rng.choice(obj)

        raise ValueError('No choice made.')

    def get_weight_object_pairs(self):
        '''Returns list of (weight, object_list) pairs in the Distribution.'''
        return list(self.weight_object_pairs)

    def set_weight_object_pairs(
            self,
            new_pairs: list[typing.Tuple[int, ObjType]]):
        '''
        Sets the Distributuion to have the given (int, object_list) pairs.
        '''
        self.weight_object_pairs = new_pairs
        self.__total_weight = sum(x[0] for x in new_pairs)

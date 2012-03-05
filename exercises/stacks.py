
DEFAULT_CARDS_PER_STACK = 8

# TODO(kamens): this will probably be persisted to the datastore in the form of a double-pickled 
# list of cards attached to UserTopics or something of the sort.
class Card(object):
    """ Holds single Card's state.
    Subclassed by ProblemCard and, in the future, stuff like VideoCard, SurveyCard, etc.
    """

    def __init__(self):
        self.card_type = "unknown"
        self.leaves_available = 4
        self.leaves_earned = 0
        self.done = False

class EndOfStackCard(Card):
    """ Single Card at end of a stack that shows all sorts of useful end-of-stack info. """

    def __init__(self):
        Card.__init__(self)

        self.card_type = "endofstack"

class ProblemCard(Card):
    """ Holds single Card's state specific to exercise problems. """

    def __init__(self):
        Card.__init__(self)

        self.card_type = "problem"
        self.exercise_name = None

# This will eventually be able to return other types of cards, like Video cards, as well.
def get_problem_stack(next_user_exercises, no_extra_cards=False):
    """ Return a stack of DEFAULT_CARDS_PER_STACK, prefilled with
    information about the first len(next_user_exercises) cards according
    to each next_user_exercise.

    If no_extra_cards is set, don't return any extra cards beyond those
    exercises supplied in next_user_exercises.
    """

    stack_size = len(next_user_exercises) if no_extra_cards else DEFAULT_CARDS_PER_STACK
    problem_cards = [ProblemCard() for i in range(stack_size)]

    # Fill in the exercise_name properties for the first N cards
    # w/ their suggested exercises. Rest will be filled in on the fly
    # as the student works.
    for ix, user_exercise in enumerate(next_user_exercises):
        if len(problem_cards) > ix:
            problem_cards[ix].exercise_name = user_exercise.exercise

    return problem_cards + [EndOfStackCard()]

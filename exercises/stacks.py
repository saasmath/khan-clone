
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

class EndOfReviewCard(Card):
    """ Single Card at end of a review that shows info about review being done or not. """

    def __init__(self):
        Card.__init__(self)
        self.card_type = "endofreview"

class ProblemCard(Card):
    """ Holds single Card's state specific to exercise problems. """

    def __init__(self, exercise_name=None):
        Card.__init__(self)
        self.card_type = "problem"
        self.exercise_name = exercise_name

# This will eventually be able to return other types of cards, like Video cards, as well.
def get_problem_stack(next_user_exercises):
    """ Return a stack of DEFAULT_CARDS_PER_STACK, prefilled with
    information about the first len(next_user_exercises) cards according
    to each next_user_exercise.
    """
    problem_cards = [ProblemCard(user_exercise.exercise) for user_exercise in next_user_exercises]

    while len(problem_cards) < DEFAULT_CARDS_PER_STACK:
        problem_cards.append(ProblemCard())

    return problem_cards + [EndOfStackCard()]

def get_review_stack(next_user_exercises):
    review_cards = [ProblemCard(user_exercise.exercise) for user_exercise in next_user_exercises]
    return review_cards + [EndOfReviewCard()]

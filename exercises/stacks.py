import random

DEFAULT_CARDS_PER_STACK = 8
MAX_CARDS_PER_REVIEW_STACK = 8

# TODO: this will probably eventually by persisted to the datastore in the form
# of a double-pickled list of cards attached to UserTopics or something similar.
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

class HappyPictureCard(Card):
    """ A surprise happy picture guaranteed to bright any student's day. """

    STACK_FREQUENCY = 200 # ~1 out of every N stacks will have one happy picture card

    def __init__(self):
        Card.__init__(self)
        self.card_type = "happypicture"
        self.leaves_available = 0

        # Todo: eventually this can use more pictures and be randomized
        self.src = "/images/power-mode/happy/toby.jpg"
        self.caption = "Toby the dog thinks you're awesome. Don't stop now."

    @staticmethod
    def should_include():
        return random.randint(0, HappyPictureCard.STACK_FREQUENCY - 1) == 0

# The idea is that this will be able to return other types of cards, like Video cards.
def get_problem_stack(next_user_exercises):
    """ Return a stack of DEFAULT_CARDS_PER_STACK, prefilled with
    information about the first len(next_user_exercises) cards according
    to each next_user_exercise.
    """
    problem_cards = [ProblemCard(user_exercise.exercise) for user_exercise in next_user_exercises]

    while len(problem_cards) < DEFAULT_CARDS_PER_STACK:
        problem_cards.append(ProblemCard())

    if HappyPictureCard.should_include():
        # Insert a happy picture card at a random spot in the stack
        ix = random.randint(1, len(problem_cards) - 1)
        problem_cards = problem_cards[:ix] + [HappyPictureCard()] + problem_cards[(ix + 1):]

    return problem_cards + [EndOfStackCard()]

def get_review_stack(next_user_exercises):
    review_cards = [ProblemCard(user_exercise.exercise) for user_exercise in next_user_exercises]

    # Cap off review stack size so it doesn't get too crazy
    review_cards = review_cards[:MAX_CARDS_PER_REVIEW_STACK]

    return review_cards + [EndOfReviewCard()]

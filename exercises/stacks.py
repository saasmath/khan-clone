
DEFAULT_CARDS_PER_STACK = 14

# TODO(kamens): this will probably be persisted to the datastore in the form of a double-pickled 
# list of cards attached to UserTopics or something of the sort.
class Card(object):
    """ Utility class for holding Card state.
    Subclassed by ProblemCard and, in the future, stuff like VideoCard, SurveyCard, etc.
    """

    def __init__(self):
        self.card_type = "unknown"
        self.leaves_earned = 0

class ProblemCard(Card):
    """ Utility class for holding Card state specific to exercise problems. """

    def __init__(self, exercise_name):
        Card.__init__(self)

        self.card_type = "problem"
        self.exercise_name = exercise_name

# TODO(kamens): this will eventually be able to handle multiple exercises, 
# topics, and probably eventually return other types of cards.
def get_problem_stack(exercise):
    return [ProblemCard(exercise.name) for i in range(DEFAULT_CARDS_PER_STACK)]

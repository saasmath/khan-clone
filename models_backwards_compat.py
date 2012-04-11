""" This file exists for the purpose of ensuring rollback safety during
a refactor of models.py.

We need to create aliases to the models module from the newly refactored
modules in order for entities that were pickled in the new code to play
nice with the old code during depickle.

We will want to work our way out of this root problem eventually, but at the
moment we are trying to re-stabilize around the new refactor.

TODO(kamens): remove this after refactor stabilizes and we won't be rolling back
"""

import models

import sys
sys.modules['backup_model'] = models
sys.modules['exercise_video_model'] = models
sys.modules['exercise_models'] = models
sys.modules['obsolete_models'] = models
sys.modules['parent_signup_model'] = models
sys.modules['promo_record_model'] = models
sys.modules['setting_model'] = models
sys.modules['summary_log_models'] = models
sys.modules['topic_models'] = models
sys.modules['user_models'] = models
sys.modules['video_models'] = models
sys.modules['url_model'] = models

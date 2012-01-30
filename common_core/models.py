from __future__ import absolute_import
import os
import logging

from google.appengine.ext import db

from models import Exercise, Video

COMMON_CORE_SEPARATOR = '_'
COMMON_CORE_BASE_URL = 'http://www.corestandards.org/the-standards/mathematics/'
COMMON_CORE_GRADE_URLS = {
        "K": "kindergarten/",
        "1": "grade-1/",
        "2": "grade-2/",
        "3": "grade-3/",
        "4": "grade-4/",
        "5": "grade-5/",
        "6": "grade-6/",
        "7": "grade-7/",
        "8": "grade-8/",
        "9-12": ""
    }

COMMON_CORE_DOMAIN_URLS = {
        "A-APR": "high-school-algebra/arithmetic-with-polynomials-and-rational-functions/",
        "A-CED": "high-school-algebra/creating-equations/",
        "A-REI": "high-school-algebra/reasoning-with-equations-and-inequalities/",
        "A-SSE": "high-school-algebra/seeing-structure-in-expressions/",
        "CC": "counting-and-cardinality/",
        "EE": "expressions-and-equations/",
        "F": "functions/",
        "F-BF": "high-school-functions/building-functions/",
        "F-IF": "high-school-functions/interpreting-functions/",
        "F-LE": "high-school-functions/linear-quadratic-and-exponential-models/",
        "F-TF": "high-school-functions/trigonometric-functions/",
        "G": "geometry/",
        "G-C": "high-school-geometry/circles/",
        "G-CO": "high-school-geometry/congruence/",
        "G-GMD": "high-school-geometry/geometric-measurement-and-dimension/",
        "G-GPE": "high-school-geometry/expressing-geometric-properties-with-equations/",
        "G-MG": "high-school-geometry/modeling-with-geometry/",
        "G-SRT": "high-school-geometry/similarity-right-triangles-and-trigonometry/",
        "MD": "measurement-and-data/",
        "MP": "standards-for-mathematical-practice/",
        "N-CN": "hs-number-and-quantity/the-complex-number-system/",
        "N-Q": "hs-number-and-quantity/quantities/",
        "N-RN": "hs-number-and-quantity/the-real-number-system/",
        "N-VM": "hs-number-and-quantity/vector-and-matrix-quantities/",
        "NBT": "number-and-operations-in-base-ten/",
        "NF": "number-and-operations-fractions/",
        "NS": "the-number-system/",
        "OA": "operations-and-algebraic-thinking/",
        "RP": "ratios-and-proportional-relationships/",
        "S": "using-probability-to-make-decisions/",
        "S-CP": "hs-statistics-and-probability/conditional-probability-and-the-rules-of-probability/",
        "S-IC": "hs-statistics-and-probability/making-inferences-and-justifying-conclusions/",
        "S-ID": "hs-statistics-and-probability/interpreting-categorical-and-quantitative-data/",
        "S-MD": "hs-statistics-and-probability/using-probability-to-make-decisions/",
        "SP": "statistics-and-probability"
    }

COMMON_CORE_DOMAINS = {
        "A-APR": "Arithmetic with Polynomials and Rational Expressions",
        "A-CED": "Creating Equations*",
        "A-REI": "Reasoning with Equations and Inequalities",
        "A-SSE": "Seeing Structure in Expressions",
        "CC": "Counting and Cardinality",
        "EE": "Expressions and Equations",
        "F": "Functions",
        "F-BF": "Building Functions",
        "F-IF": "Interpreting Functions",
        "F-LE": "Linear, Quadratic, and Exponential Models",
        "F-TF": "Trigonometric Functions",
        "G": "Geometry",
        "G-C": "Circles",
        "G-CO": "Congruence",
        "G-GMD": "Geometric Measurement and Dimension",
        "G-GPE": "Expressing Geometric Properties with Equations",
        "G-MG": "Modeling with Geometry",
        "G-SRT": "Similarity, Right Triangles, and Trigonometry",
        "MD": "Measurement and Data",
        "MP": "Standards for Mathematical Practice",
        "N-CN": "The Complex Number System",
        "N-Q": "Quantities",
        "N-RN": "The Real Number System",
        "N-VM": "Vector and Matrix Quantities",
        "NBT": "Number and Operations in Base Ten",
        "NF": "Number and Operations--Fractions",
        "NS": "The Number System",
        "OA": "Operations and Algebraic Thinking",
        "RP": "Ratios and Proportional Relationships",
        "S": "Using Probability to Make Decisions",
        "S-CP": "Conditional Probability & the Rules of Probability",
        "S-IC": "Making Inferences and Justifying Conclusions",
        "S-ID": "Interpreting Categorical and Quantitative Data",
        "S-MD": "Using Probability to Make Decisions",
        "SP": "Statistics and Probability"
    }

class CommonCoreMap(db.Model):
    standard = db.StringProperty()
    grade = db.StringProperty()
    domain = db.StringProperty()
    domain_code = db.StringProperty()
    level = db.StringProperty()
    cc_url = db.StringProperty()
    exercises = db.ListProperty(db.Key)
    videos = db.ListProperty(db.Key)

    def get_entry(self, lightweight=False):
        entry = {}
        entry['standard'] = self.standard
        entry['grade'] = self.grade
        entry['domain'] = self.domain
        entry['domain_code'] = self.domain_code
        entry['level'] = self.level
        entry['cc_url'] = self.cc_url
        entry['exercises'] = []
        entry['videos'] = []
        for key in self.exercises:
            if lightweight:
                ex = db.get(key)
                entry['exercises'].append({ "title": ex.display_name, "url": ex.ka_url })
            else:
                entry['exercises'].append(db.get(key))
        for key in self.videos:
            if lightweight:
                v = db.get(key)
                entry['videos'].append({ "title": v.title, "url": v.url })
            else:
                entry['videos'].append(db.get(key))

        return entry

    @staticmethod
    def get_all():
        query = CommonCoreMap.all()
        all_entries = []
        for e in query:
            all_entries.append(e.get_entry())
        return all_entries

    @staticmethod
    def get_all_lightweight():
        query = CommonCoreMap.all()
        all_entries = []
        for e in query:
            all_entries.append(e.get_entry(lightweight=True))
        return all_entries

    def update_standard(self, standard):
        self.standard = standard
        cc_components = self.standard.split(COMMON_CORE_SEPARATOR)
        self.grade = cc_components[1]
        self.domain = COMMON_CORE_DOMAINS[cc_components[2]]
        self.domain_code = cc_components[2]
        self.level = cc_components[3]
        self.cc_url = COMMON_CORE_BASE_URL + COMMON_CORE_GRADE_URLS[self.grade] + COMMON_CORE_DOMAIN_URLS[self.domain_code] + "#"
        if self.grade != "9-12":
           self.cc_url += self.grade.lower() + "-"
        self.cc_url += self.domain_code.lower() + "-" + self.level.split('.')[0]

        return

    def update_exercise(self, exercise_name):
        ex = Exercise.all().filter('name =', exercise_name).get()
        if ex is not None:
            if self.standard not in ex.cc_standards:
                ex.cc_standards.append(self.standard)
                ex.put()

            if ex.key() not in self.exercises:
                self.exercises.append(ex.key())
        else:
            logging.info("Exercise %s not in datastore" % exercise_name)

        return

    def update_video(self, video_youtube_id):
        v = Video.all().filter('youtube_id =', video_youtube_id).get()
        if v is not None:
            if self.standard not in v.cc_standards:
                v.cc_standards.append(self.standard)
                v.put()

            if v.key() not in self.videos:
                self.videos.append(v.key())
        else:
            logging.info("Youtube ID %s not in datastore" % video_youtube_id)

        return

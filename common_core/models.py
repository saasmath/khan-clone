from __future__ import absolute_import
import os
import logging

from google.appengine.ext import db

from models import Exercise, Video

COMMON_CORE_SEPARATOR = '_'
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
        "S-CP": "Using Probability to Make Decisions",
        "S-IC": "Making Inferences and Justifying Conclusions",
        "S-ID": "Interpreting Categorical and Quantitative Data",
        "SP": "Statistics and Probability"
    }

class CommonCoreMap(db.Model):
    standard = db.StringProperty()
    grade = db.StringProperty()
    domain = db.StringProperty()
    domain_code = db.StringProperty()
    level = db.StringProperty()
    exercises = db.ListProperty(db.Key)
    videos = db.ListProperty(db.Key)

    def get_entry(self, lightweight=False):
        entry = {}
        entry['standard'] = self.standard
        entry['grade'] = self.grade
        entry['domain'] = self.domain
        entry['domain_code'] = self.domain_code
        entry['level'] = self.level
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
        return

    def update_exercise(self, exercise_name):
        ex = Exercise.all().filter('name =', exercise_name).get()
        if ex is not None and self.standard not in ex.cc_standards:
            ex.cc_standards.append(self.standard)
            ex.put()

            if exercise_name not in self.exercises:
                self.exercises.append(ex.key())
        else:
            logging.info("Exercise %s not in datastore" % exercise_name)

        return

    def update_video(self, video_youtube_id):
        v = Video.all().filter('youtube_id =', video_youtube_id).get()
        if v is not None and self.standard not in v.cc_standards:
            v.cc_standards.append(self.standard)
            v.put()

            if video_youtube_id not in self.videos:
                self.videos.append(v.key())
        else:
            logging.info("Youtube ID %s not in datastore" % video_youtube_id)

        return

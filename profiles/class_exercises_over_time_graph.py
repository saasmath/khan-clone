import logging

from google.appengine.api import users

from datetime import datetime, timedelta
import models
import util

class ExerciseData:
        def __init__(self, nickname, exid, days_until_proficient, proficient_date):
            self.nickname = nickname
            self.exid = exid
            self.days_until_proficient = days_until_proficient
            self.proficient_date = proficient_date

        def display_name(self):
            return  models.Exercise.to_display_name(self.exid)

def class_exercises_over_time_graph_context(user_data, student_list):

    if not user_data:
        return {}

    all_students_data = user_data.get_students_data()
    
    if student_list:
        students_data = student_list.get_students_data()
    else:
        students_data = all_students_data    
    
    cache = models.ClassUserExerciseCache.get_by_key_name(models.ClassUserExerciseCache.get_key_name(user_data))
    if cache is not None: 
        #don't bother trying to update if the last update was less than 5 minutes ago
        if cache.date_updated > datetime.now() + timedelta(seconds=300) and cache.update_data(user_data):   
            cache.put() 
    else: 
        cache = models.ClassUserExerciseCache.generate(user_data)

    if students_data != all_students_data:
        dict_student_exercises = dict((k, cache.data[k.nickname]) for k in students_data)
    else:
        dict_student_exercises = cache.data

    return {
            "dict_student_exercises": dict_student_exercises,
            "user_data_students": students_data,
            "c_points": reduce(lambda a, b: a + b, map(lambda s: s.points, students_data), 0)
            }


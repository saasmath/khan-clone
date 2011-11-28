from jinja2.utils import escape
from templatefilters import escapejs

import models
import util
from itertools import izip
import datetime
import logging
import templatefilters

def truncate_to(s, length):
    if len(s) > length:
        return s[18:] + '...'
    else:
        return s

def class_progress_report_graph_context(user_data, student_list):

    if not user_data:
        return {}

    list_students = None
    if student_list:
        list_students = student_list.get_students_data()
    else:
        list_students = user_data.get_students_data()

    student_email_pairs = [(escape(s.email), truncate_to(s.nickname, 18)) for s in list_students]
    emails_escapejsed = [escapejs(s.email) for s in list_students]

    exercises_all = models.Exercise.get_all_use_cache()
    user_exercise_graphs = models.UserExerciseGraph.get(list_students)

    exercises_found = []

    for exercise in exercises_all:
        for user_exercise_graph in user_exercise_graphs:
            graph_dict = user_exercise_graph.graph_dict(exercise.name)
            if graph_dict and graph_dict["total_done"]:
                exercises_found.append(exercise)
                break

    exercise_names = [(e.name, e.display_name, escapejs(e.name)) for e in exercises_found]
    exercise_list = [{'name': e.name, 'display_name': e.display_name} for e in exercises_found]

    exercise_data = {}

    for (student, student_email_pair, escapejsed_student_email, user_exercise_graph) in izip(list_students, student_email_pairs, emails_escapejsed, user_exercise_graphs):

        student_email = student.email
        escaped_nickname = escape(student.nickname)
        escaped_student_email = student_email_pair[0]
        truncated_nickname = student_email_pair[1]

        student_review_exercise_names = user_exercise_graph.review_exercise_names()

        for (exercise, (_, exercise_display, exercise_name_js)) in izip(exercises_found, exercise_names):

            exercise_name = exercise.name
            graph_dict = user_exercise_graph.graph_dict(exercise_name)

            status = ""

            if graph_dict["proficient"]:

                if exercise_name in student_review_exercise_names:
                    status = "Review"
                else:
                    status = "Proficient"
                    if not graph_dict["explicitly_proficient"]:
                        status = "Proficient (due to proficiency in a more advanced module)"
                        
            elif graph_dict["struggling"]:
                status = "Struggling"
            elif graph_dict["total_done"] > 0:
                status = "Started"

            if not exercise_data.has_key(student_email):
                exercise_data[student_email] = {
                    'email': student.email,
                    'nickname': student.nickname,
                    'exercises': []
                }

            if len(status) > 0:
                exercise_data[student_email]['exercises'].append({
                    "status": status,
                    "progress": graph_dict["progress"],
                    "total_done": graph_dict["total_done"],
                    "last_done": graph_dict["last_done"] if graph_dict["last_done"] and graph_dict["last_done"].year > 1 else '',
                    "last_done_ago": templatefilters.timesince_ago(graph_dict["last_done"]) if graph_dict["last_done"] and graph_dict["last_done"].year > 1 else ''
                })
            else:
                exercise_data[student_email]['exercises'].append({
                    "name": exercise_name,
                    "status": status,
                })

    student_row_data = [ data for key, data in exercise_data.iteritems() ]

    return {
        'exercise_names': exercise_list,
        'exercise_data': student_row_data,
        'coach_email': user_data.email,
        'c_points': reduce(lambda a, b: a + b, map(lambda s: s.points, list_students), 0)
    }

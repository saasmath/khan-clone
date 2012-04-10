"""A database entity connecting a list of students with a single coach.

This list is visible when visiting
   http://www.khanacademy.org/class_profile
TODO(csilvers): is that right?
"""

from google.appengine.ext import db

from user_models import UserData


class StudentList(db.Model):
    """A list of students associated with a single coach."""
    name = db.StringProperty()
    coaches = db.ListProperty(db.Key)

    def delete(self, *args, **kwargs):
        self.remove_all_students()
        db.Model.delete(self, *args, **kwargs)

    def remove_all_students(self):
        students = self.get_students_data()
        for s in students:
            s.student_lists.remove(self.key())
        db.put(students)

    @property
    def students(self):
        return UserData.all().filter("student_lists = ", self.key())

    # these methods have the same interface as the methods on UserData
    def get_students_data(self):
        return [s for s in self.students]

    @staticmethod
    def get_for_coach(key):
        query = StudentList.all()
        query.filter("coaches = ", key)
        return query


# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""CloudSim dashboard module."""

__author__ = 'ammp'

import time
import webapp2
import os
import datetime
import sys

import cgi
import urllib

from common import safe_dom
from common import tags
from controllers import utils
from controllers.utils import BaseHandler
from controllers import cloudsim_utils
from models import custom_modules

from models import models
from models import utils
from models import transforms
from models.config import ConfigProperty
from models.config import ConfigPropertyEntity
from models.courses import Course
from models.models import Student
from models.models import StudentProfileDAO
from models.models import TransientStudent
from models.models import StudentAnswersEntity
from models.roles import Roles

from controllers import assessments

from google.appengine.ext import db

from cloudsim_rest_api import CloudSimRestApi

class CloudsimAssessmentHandler(BaseHandler):
    """Handles simulation launches."""

    @db.transactional(xg=True)
    def update_assessment_transaction(
        self, email, assessment_type, new_answers, score):
        """Stores answer and updates user scores.

        Args:
            email: the student's email address.
            assessment_type: the title of the assessment.
            new_answers: the latest set of answers supplied by the student.
            score: the numerical assessment score.

        Returns:
            the student instance.
        """
        student = Student.get_enrolled_student_by_email(email)
        course = self.get_course()

        # It may be that old Student entities don't have user_id set; fix it.
        if not student.user_id:
            student.user_id = self.get_user().user_id()

        answers = StudentAnswersEntity.get_by_key_name(student.user_id)
        if not answers:
            answers = StudentAnswersEntity(key_name=student.user_id)
        answers.updated_on = datetime.datetime.now()

        utils.set_answer(answers, assessment_type, new_answers)

        assessments.store_score(course, student, assessment_type, score)

        student.put()
        answers.put()   

    def post(self):
        """Handles POST requests"""

        print "now in handler"
        student = self.personalize_page_and_get_enrolled()
        if not student:
            print "not student"
            return

        self.template_value['cloudsim_ip'] = student.cloudsim_ip
        self.template_value['cloudsim_uname'] = student.cloudsim_uname
        self.template_value['cloudsim_passwd'] = student.cloudsim_passwd
        self.template_value['cloudsim_simname'] = student.cloudsim_simname

        action = self.request.get('action')
        assessment_name = self.request.get('name')


        print action

        if action == "launch":
            try:
                task_dict = {}
                task_dict['task_title'] = 'Cloudsim-Ed_Actuation_Challenge'
                task_dict['ros_package'] = 'cloudsim_ed_actuation'
                task_dict['ros_launch'] = 'cloudsim_ed_actuation_challenge_01.launch'
                task_dict['launch_args'] = ''
                task_dict['timeout'] = '3600'
                task_dict['latency'] = '0'
                task_dict['uplink_data_cap'] = '0'
                task_dict['downlink_data_cap'] = '0'
                task_dict['local_start'] = _get_now_str(-1)
                task_dict['local_stop'] = _get_now_str(1)
                task_dict['bash_src'] =  ''  
                task_dict['vrc_id'] = 1
                task_dict['vrc_num'] = 1

                cloudsim_api = CloudSimRestApi(student.cloudsim_ip, student.cloudsim_uname, student.cloudsim_passwd)
                task_id = cloudsim_api.create_task(student.cloudsim_simname, task_dict)
                cloudsim_api.start_task(student.cloudsim_simname, task_id)
                alert = "Task Created"

                cloudsim_api = CloudSimRestApi(student.cloudsim_ip, student.cloudsim_uname, student.cloudsim_passwd)

            except:
                e = sys.exc_info()[0]
                print(e)
                alert = "An error occured while connecting to the simulator; " + str(e)

        elif action == "reset":
            print name
    
        elif action == "getscore":
            print name

            course = self.get_course()
            print course
            assessment_type = assessment_name

            answers = ''
            score = 5

            # Record assessment transaction.
            student = self.update_assessment_transaction(
                student.key().name(), assessment_type, answers, score)

        self.redirect('/assessment?name=Lab1')


class CloudsimCredentialsEditHandler(BaseHandler):
    """Handles edits to student cloudsim credentials."""

    def post(self):
        """Handles POST requests."""
        student = self.personalize_page_and_get_enrolled()
        if not student:
            print "not student"
            return

        if not self.assert_xsrf_token_or_fail(self.request, 'student-edit'):
            print "token fail"            
            return

        Student.edit_cloudsim_credentials(self.request.get('cloudsim_ip'), 
                            self.request.get('cloudsim_uname'), self.request.get('cloudsim_passwd'),
                            self.request.get('cloudsim_simname'))
        
        self.redirect('/student/home')

class CloudsimTestLaunchHandler(BaseHandler):
    """Handler for launch page."""

    def get(self):
        """Handles GET requests."""
        status = "Connect to a simulator to view available tasks"
        alert = ""
        task_list = ""

        student = self.personalize_page_and_get_enrolled()
        if not student:
            return

        name = student.name
        profile = student.profile
        if profile:
            name = profile.nick_name

        self.template_value['cloudsim_ip'] = student.cloudsim_ip
        self.template_value['cloudsim_uname'] = student.cloudsim_uname
        self.template_value['cloudsim_passwd'] = student.cloudsim_passwd
        self.template_value['cloudsim_simname'] = student.cloudsim_simname

        print student.cloudsim_passwd

        self.template_value['navbar'] = {}
        self.template_value['status'] = status
        self.render('cloudlaunch.html')

    def post(self):
        """Handles POST requests."""

        def _get_now_str(days_offset=0):
                """
                Returns a utc string date time format of now, with optional
                offset.
                """
                dt = datetime.timedelta(days=days_offset)
                now = datetime.datetime.utcnow()
                t = now - dt
                s = t.isoformat()
                return s
        
        status = "Connect to a Simulator to view tasks"
        alert = ""
        task_list = ""

        student = self.personalize_page_and_get_enrolled()
        if not student:
            return

        name = student.name
        profile = student.profile
        if profile:
            name = profile.nick_name

        action = self.request.get("action", '')
 
        if action == "checkstatus":
            try:
                simulator_name = self.request.get('simulator_name')
                cloudsim_api = CloudSimRestApi(student.cloudsim_ip, student.cloudsim_uname, student.cloudsim_passwd) 
                task_list = cloudsim_api.get_tasks(simulator_name)
                status = ""

            except:
                e = sys.exc_info()[0]
                print(e)
                alert = "An error occured while connecting to the simulator; " + str(e)

        elif action == "createtask":
            try:
                student = self.personalize_page_and_get_enrolled()
                if not student:
                    return

                course = self.get_course()
                name = student.name
                profile = student.profile
                if profile:
                    name = profile.nick_name
               
                simulator_name = self.request.get('simulator_name')
                task_name = self.request.get('task_name')

                task_title = self.request.get('task_title')
                ros_package = self.request.get('ros_package')
                launch_filename = self.request.get('launch_filename')
                bash_filename = self.request.get('bash_filename')

                task_dict = {}
                task_dict['task_title'] = task_title
                task_dict['ros_package'] = ros_package
                task_dict['ros_launch'] = launch_filename
                task_dict['launch_args'] = ''
                task_dict['timeout'] = '3600'
                task_dict['latency'] = '0'
                task_dict['uplink_data_cap'] = '0'
                task_dict['downlink_data_cap'] = '0'
                task_dict['local_start'] = _get_now_str(-1)
                task_dict['local_stop'] = _get_now_str(1)
                task_dict['bash_src'] =  bash_filename  
                task_dict['vrc_id'] = 1
                task_dict['vrc_num'] = 1

                cloudsim_api = CloudSimRestApi(student.cloudsim_ip, student.cloudsim_uname, student.cloudsim_passwd)
                task_id = cloudsim_api.create_task(simulator_name, task_dict)
                task_list = cloudsim_api.get_tasks(simulator_name)
                status = ""
                #cloudsim_api.start_task(session.sim_name, task_id)
                alert = "Task Created"
            except:
                e = sys.exc_info()[0]
                print(e)
                alert = "An error occured while launching task; " + str(e)


        self.template_value['navbar'] = {}
        self.template_value['status'] = status
        self.template_value['alert'] = alert
        self.template_value['task_list'] = task_list

        self.template_value['cloudsim_ip'] = student.cloudsim_ip
        self.template_value['cloudsim_uname'] = student.cloudsim_uname
        self.template_value['cloudsim_passwd'] = student.cloudsim_passwd
        self.template_value['cloudsim_simname'] = student.cloudsim_simname

        self.render('cloudlaunch.html')
        

# Coursebuilder
def register_module():
    """Registers this module in the registry."""

    # register custom tag
    #tags.Registry.add_tag_binding('cloudsim', CloudsimTag)

    # register handlers
    # zip_handler = ('/khan-exercises', sites.make_zip_handler(ZIP_FILE))
    credentials_handler = ('/cloudlaunch/edit', CloudsimCredentialsEditHandler)
    launch_handler = ('/cloudlaunch', CloudsimTestLaunchHandler)
    assessment_handler = ('/cloudlaunch/assess', CloudsimAssessmentHandler)

    # register module
    global custom_module
    custom_module = custom_modules.Module(
        'Cloudsim Test',
        'A set of pages for starting/stopping Cloudsim machines via '
        'Course Builder.',
        [], [launch_handler, credentials_handler, assessment_handler])
    return custom_module        


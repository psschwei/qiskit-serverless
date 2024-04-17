"""Tests for serializer functions."""

import os
import json

from django.contrib.auth import models
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files import File
from rest_framework.test import APITestCase
from api.v1.serializers import (
    JobConfigSerializer,
    UploadProgramSerializer,
    RunExistingProgramSerializer,
    RunExistingJobSerializer,
)
from api.models import JobConfig, Program


class SerializerTest(APITestCase):
    """Tests for serializer."""

    fixtures = ["tests/fixtures/fixtures.json"]

    def test_JobConfigSerializer(self):
        data = '{"workers": null, "min_workers": 1, "max_workers": 5, "auto_scaling": true}'
        config_serializer = JobConfigSerializer(data=json.loads(data))
        assert config_serializer.is_valid()
        jobconfig = config_serializer.save()

        entry = JobConfig.objects.get(id=jobconfig.id)
        assert not entry.workers
        assert entry.min_workers == 1
        assert entry.max_workers == 5
        assert entry.auto_scaling

        data = '{"workers": 3, "min_workers": null, "max_workers": null, "auto_scaling": null}'
        config_serializer = JobConfigSerializer(data=json.loads(data))
        assert config_serializer.is_valid()
        jobconfig = config_serializer.save()

        entry = JobConfig.objects.get(id=jobconfig.id)
        assert entry.workers == 3
        assert not entry.min_workers
        assert not entry.max_workers
        assert not entry.auto_scaling

    def test_upload_program_serializer_creates_program(self):
        path_to_resource_artifact = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "resources",
            "artifact.tar",
        )
        file_data = File(open(path_to_resource_artifact, "rb"))
        upload_file = SimpleUploadedFile(
            "artifact.tar", file_data.read(), content_type="multipart/form-data"
        )

        user = models.User.objects.get(username="test_user")

        title = "Hello world"
        entrypoint = "pattern.py"
        arguments = "{}"
        dependencies = "[]"

        data = {}
        data["title"] = title
        data["entrypoint"] = entrypoint
        data["arguments"] = arguments
        data["dependencies"] = dependencies
        data["artifact"] = upload_file

        serializer = UploadProgramSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        program: Program = serializer.save(author=user)
        self.assertEqual(title, program.title)
        self.assertEqual(entrypoint, program.entrypoint)
        self.assertEqual(dependencies, program.dependencies)

    def test_upload_program_serializer_check_empty_data(self):
        data = {}

        serializer = UploadProgramSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        errors = serializer.errors
        self.assertListEqual(["title", "entrypoint", "artifact"], list(errors.keys()))

    def test_upload_program_serializer_fails_at_validation(self):
        path_to_resource_artifact = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "resources",
            "artifact.tar",
        )
        file_data = File(open(path_to_resource_artifact, "rb"))
        upload_file = SimpleUploadedFile(
            "artifact.tar", file_data.read(), content_type="multipart/form-data"
        )

        title = "Hello world"
        entrypoint = "pattern.py"
        arguments = {}
        dependencies = []

        data = {}
        data["title"] = title
        data["entrypoint"] = entrypoint
        data["artifact"] = upload_file
        data["arguments"] = arguments
        data["dependencies"] = dependencies

        serializer = UploadProgramSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        errors = serializer.errors
        self.assertListEqual(["dependencies"], list(errors.keys()))

    def test_run_existing_program_serializer_check_emtpy_data(self):
        data = {}

        serializer = RunExistingProgramSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        errors = serializer.errors
        self.assertListEqual(["title", "arguments", "config"], list(errors.keys()))

    def test_run_existing_program_serializer_fails_at_validation(self):
        data = {
            "title": "Program",
            "arguments": {},
            "config": {},
        }

        serializer = RunExistingProgramSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        errors = serializer.errors
        self.assertListEqual(["arguments", "config"], list(errors.keys()))

    def test_run_existing_program_serializer_config_json(self):
        assert_json = {
            "workers": None,
            "min_workers": 1,
            "max_workers": 5,
            "auto_scaling": True,
        }
        data = {
            "title": "Program",
            "arguments": "{}",
            "config": json.dumps(assert_json),
        }

        serializer = RunExistingProgramSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        config = serializer.data.get("config")
        self.assertEqual(type(assert_json), type(config))
        self.assertDictEqual(assert_json, config)

    def test_run_existing_job_serializer_check_empty_data(self):
        data = {}

        serializer = RunExistingJobSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_run_existing_job_serializer_creates_job(self):
        user = models.User.objects.get(username="test_user")
        program_instance = Program.objects.get(
            id="1a7947f9-6ae8-4e3d-ac1e-e7d608deec82"
        )
        arguments = "{}"

        job_serializer = RunExistingJobSerializer(data={})
        job_serializer.is_valid()
        job = job_serializer.save(
            arguments=arguments,
            author=user,
            carrier={},
            token="my_token",
            program=program_instance,
            config=None,
        )
        env_vars = json.loads(job.env_vars)
        self.assertTrue(env_vars["PROGRAM_ENV1"] == "VALUE1")
        self.assertTrue(env_vars["PROGRAM_ENV2"] == "VALUE2")
        self.assertIsNotNone(job)
PROJECT ?= bt-mvp-dev-eu
REGION  ?= europe-west2

.PHONY: bootstrap init plan apply sample test destroy

bootstrap:          ## one-time: state bucket, Artifact Registry, CI SA, WIF
	cd bootstrap && terraform init && terraform apply

init:
	cd terraform && terraform init

plan:
	cd terraform && terraform plan

apply:              ## build image + provision everything
	cd terraform && terraform apply

sample:             ## generate the demo PDF and drop it in the intake bucket
	cd samples && python3 make_sample.py && \
	gcloud storage cp sample_submission.pdf gs://$(PROJECT)-uw-intake/

test:               ## tail the latest workflow execution
	gcloud workflows executions list uw-pipeline --location=$(REGION) --limit=3

destroy:
	cd terraform && terraform destroy

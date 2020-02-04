redVersion: '9'
cli:
  cwlVersion: 'v1.0'
  class: 'CommandLineTool'
  baseCommand: 'echo'
  doc: 'Simple Test Script'

  inputs:
    text:
      type: 'string'
      inputBinding:
        position: 1
  outputs: {}

batches:
  - inputs:
      text: 'hello'
    outputs: {}

container:
  engine: 'docker'
  settings:
    image:
      url: 'python:3.8'
    ram: 256

execution:
  engine: "ccagency"
  settings:
    batchConcurrencyLimit: 10000000
    access:
      url: "https://agency.f4.htw-berlin.de/cctest"
      auth:
        username: "{{cc_test_agency_username}}"
        password: "{{cc_test_agency_password}}"
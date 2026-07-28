[![Terraform Version](https://img.shields.io/badge/terraform-%5E1.6-blue)](https://www.terraform.io)
[![Module Version](https://img.shields.io/badge/module-0.6.0-green)](https://registry.terraform.io/modules/netascode/nac-meraki/meraki)

# Network-as-Code Meraki Terraform

Use Terraform to operate and manage a Cisco Meraki using purpose built modules. Everything can also be executed locally (without CI/CD) following the instructions below.

## Setup

Install [Terraform](https://www.terraform.io/downloads) (>= 1.6.0), and the following Python tools:

- [nac-validate](https://github.com/netascode/nac-validate)
- [nac-test](https://github.com/netascode/nac-test)

```shell
pip install nac-validate nac-test
```

Set environment variables with the Meraki Dashboard API key:

```shell
export MERAKI_API_KEY=ABC1234
```

## Initialization

```shell
terraform init
```

This command will download all the required providers and modules from the public Terraform Registry ([https://registry.terraform.io](https://registry.terraform.io)).

## Pre-Change Validation

```shell
nac-validate data/
```

This command performs syntactic and semantic validation of YAML input files located in `data/`.

## Terraform Plan/Apply

```shell
terraform apply
```

This command will apply/deploy the desired configuration.

## Testing

```shell
nac-test --data ./data --data ./defaults.yaml --templates ./tests/templates --filters ./tests/filters --output ./tests/results
```

This command will render and execute a set of tests and provide the results in a report (`tests/results/log.html`).

## Terraform Destroy

```shell
terraform destroy
```

This command will delete all the previously created configuration.

## Documentation

Further documentation is available [here](https://netascode.cisco.com).

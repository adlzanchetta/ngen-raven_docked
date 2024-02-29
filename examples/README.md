# Examples

This folder contain examples of input files for running Raven inside (and outside) NexGen using the Docker image.

These examples are also used for testing the own Docker image. Tests are automated with Github Actions for continuous integration.

## Naming convention

Each example/test has an unique numeric id and can be categorized considering the follwoing attributes:

- ```ngnp```: NexGen number of parallel processes:
  - `1`: serial, or 
  - `2`, `3`, `...`: parallel using as much proceeses.
- ```ngts```: NexGen timestep:
  - ```h```: hourly, or 
  - ```d```: daily;
- ```ngrt```: NexGen routing:
  - ```t```: true/present, or
  - ```f```: false/absent;
- ```rvmd```: Raven model(s);
  - ```hbv```,
  - ```hecms```, or
  - ```multi```;
- ```nsub```: number of subbasins:
  - any *positive integer* value.

The naming convention for the examples/tests follows the structure:
```
id-{?}_ngnp-{?}_ngts-{?}_ngrt-{?}_rvmd-{?}_nsub-{?}
```
in which ```{?}``` is a placeholder for the value of the preceeding attribute.

Example of a valid example/test name: `id-03_ngnp-2_ngts-h_ngrt-f_rvmd-HBV_nsub-38`.

## Filesystem structure

Each valid example/test consists of a folder with the following structure:

```
{test_name}/
    data_raven-standalone/
    data_raven-in-nexgen/
```

## Testing steps

For each example/test:

1. copy subfolder `data_raven_standalone` into `/data_raven`;
2. run `Raven` having `/data_raven` as working directory;
3. store generated `TODO` file at `/data_comparison`;
4. clean folder `/data`;
5. copy subfolder `data_raven_nexgen` into `/data`;
6. run the specific `ngen` having `/data/3_output` as working directort;
7. store generted `TODO` file at `/data_comparison`;
8. clean folder `/data`;
9. compare content of files `TODO` and `TODO` at `/data_comparison`;
10. **PASS** if both files are present and contents match, **FAIL** otherwise;
11. clean folder `/data_comparison`.

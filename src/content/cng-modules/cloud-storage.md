## Overview

Until now, we've treated data as "files on a disk." But when you scale to
petabytes of satellite imagery or global vector datasets, you can't keep
downloading files. You need to treat **Object Storage** (AWS S3, Google Cloud
Storage, Azure Blob Storage) as your primary file system.

Object storage is not a normal file system. You can't `cd` into it, and you
can't "open" a file in the traditional sense. However, it has one superpower
that makes Cloud-Native Geospatial possible: **HTTP Range Requests**.

## Key Concepts

### 1. Object Storage vs. Filesystem

Object storage treats every file as a flat, addressable blob with a key
(path) and metadata — there is no directory hierarchy, no locking, and no
in-place editing. This design scales horizontally without limit and enables
global distribution, but it means all access must go through an HTTP API.
Libraries like `fsspec` and `s3fs` paper over this difference so Python code
can treat object storage like a local filesystem.

### 2. HTTP Range Requests

The HTTP `Range` header lets a client ask for a specific byte range within a
file without downloading the whole thing. Cloud-native formats like COG, Zarr,
and GeoParquet are all designed so that a single small range request retrieves
the header or metadata needed to locate exactly the data you need, followed by
one or more targeted reads for just those bytes. This is what makes streaming
petabyte-scale imagery feasible on a laptop.

### 3. Access Patterns and Cost

Reading data from object storage is cheap but not free. Egress costs (moving
data out of a cloud region) and per-request API fees add up quickly at scale.
Strategies that reduce cost include: choosing chunk sizes that match your
analysis pattern, using caching file systems (`fsspec.implementations.caching`)
for repeat reads, co-locating compute in the same cloud region as data, and
preferring formats that minimize the number of requests needed to answer a
query.

## 1. Range Requests: The Cloud-Native Secret

Imagine you have a 1GB Cloud Optimized GeoTIFF (COG) on S3. You only need to
look at a small farm in the corner of the image (about 1MB of data).

- **Traditional approach**: Download the 1GB file, open it locally, and find the
  farm.
- **Cloud-Native approach**: Read the 10KB header to find where the farm's
  pixels are stored, then issue a **Range Request** to pull only that 1MB chunk.

Libraries like `fsspec` and `s3fs` make this look like standard Python file
operations, opening a remote file as a seekable byte stream and downloading only
the bytes you actually read.

## 2. Access Control: Requester Pays

Some public datasets (like Sentinel-2 L1C on AWS) are free to use but charge for
"egress" (the cost of moving data out of the bucket's region). To protect their
budgets, data providers enable **Requester Pays**.

When you access these buckets, you must have valid AWS credentials and
explicitly acknowledge that you accept the transfer cost. In Python, this is a
single flag passed to `s3fs.S3FileSystem`.

### Setting up AWS Credentials

1. **Get Keys**: In the AWS Console, go to **IAM** -> **Users** -> **Security
   Credentials** -> **Create Access Key**.
2. **Configure Locally**: Install the AWS CLI and run `aws configure`, or set
   environment variables:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

## 3. Performance: Caching

Object storage is often slower than local disk. To speed up repeat access, you
can use a **CachingFileSystem**. This will save chunks to your local disk as you
read them, so second reads are nearly instant.

## Practical Exercises

A benchmark script demonstrates range request performance by timing partial reads
of different sizes from a large Landsat GeoTIFF, then shows the Requester Pays
pattern with a windowed crop from a Sentinel-2 file on S3.



## Next Steps

Now that you've mastered the underlying storage patterns, you're ready to see
how these enable the next generation of spatial intelligence in **AI
& Machine Learning**.

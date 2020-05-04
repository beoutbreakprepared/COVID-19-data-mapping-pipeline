If you want to run this server locally, you will need the following:

|Name|Why|Debian/Ubuntu package|
|--|--|--|
|Java|Run the Closure compiler|openjdk-11-jre|
|Python 3|Run the server|`python3`|
|Pandas|Massage the data for server ingestion|`python3-pandas`|
|SASS|Generate CSS from SCSS|`ruby-sass`|

The Closure compiler is also a dependency for deployment, but it will be automatically fetched when necessary.

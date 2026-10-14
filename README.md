# npkg
# Download the main branch as a .tar.gz (no git required)
curl -fL https://codeload.github.com/zhexhem/npkg/tar.gz/refs/heads/main -o npkg.tar.gz

# Extract
tar -xzf npkg.tar.gz

# The extracted directory is named npkg-main/
cd npkg-main

curl -fL https://codeload.github.com/zhexhem/npkg/tar.gz/refs/heads/main \
  | tar -xz --strip-components=1 -C ./npkg
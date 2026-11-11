Name:		apache-sshd
Version:	2.15.0
Release:	1
Summary:	Apache MINA SSHD
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/apache/mina-sshd
# Tag sshd-2.15.0. Gradle 9.9.1 pins sshd-core, sshd-osgi, sshd-scp, and sshd-sftp.
Source0:	https://github.com/apache/mina-sshd/archive/refs/tags/sshd-%{version}.tar.gz#/apache-sshd-%{version}.tar.gz
# tomcat-apr 5.5 JNI is not packaged. The NIO local agent is the upstream fallback.
Patch0:		apache-sshd-2.15.0-no-apr.patch
# Bouncy Castle 1.86 moved ML-KEM out of org.bouncycastle.pqc.crypto.mlkem.
Patch1:		apache-sshd-2.15.0-mlkem.patch

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	mvn(org.slf4j:slf4j-api) >= 2.0.17
BuildRequires:	mvn(net.i2p.crypto:eddsa) = 0.3.0
BuildRequires:	mvn(org.bouncycastle:bcprov-jdk18on)
BuildRequires:	mvn(org.bouncycastle:bcpkix-jdk18on)
BuildRequires:	mvn(org.bouncycastle:bcutil-jdk18on)

%description
Apache MINA SSHD %{version} is the pure Java SSH library Gradle 9.9.1 loads.
This package builds sshd-common, sshd-core, sshd-scp, sshd-sftp, and the
sshd-osgi bundle (common plus core) from source.

%prep
%autosetup -n mina-sshd-sshd-%{version} -p1
find . \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -delete

%build
set -eo pipefail
CP="%{_javadir}/slf4j-api.jar:%{_javadir}/eddsa.jar:%{_javadir}/bcprov-jdk18on.jar:%{_javadir}/bcpkix-jdk18on.jar:%{_javadir}/bcutil-jdk18on.jar"

find sshd-common/src/main/java -name '*.java' > common.list
test "$(wc -l < common.list)" -eq 406
mkdir -p classes-common
javac --release 8 -encoding UTF-8 -cp "$CP" -d classes-common @common.list
cp -a sshd-common/src/main/filtered-resources/. classes-common/
cat > classes-common/org/apache/sshd/sshd-version.properties << EOF
groupId=org.apache.sshd
artifactId=sshd-common
version=%{version}
sshd-version=apache-sshd-%{version}
EOF

find sshd-core/src/main/java -name '*.java' ! -path '*/agent/unix/*' > core.list
test "$(wc -l < core.list)" -eq 356
test "$(find sshd-core/src/main/java -path '*/agent/unix/*.java' | wc -l)" -eq 8
mkdir -p classes-core
javac --release 8 -encoding UTF-8 -cp "$CP:classes-common" -d classes-core @core.list
cp -a sshd-core/src/main/filtered-resources/. classes-core/

find sshd-scp/src/main/java -name '*.java' > scp.list
test "$(wc -l < scp.list)" -eq 39
mkdir -p classes-scp
javac --release 8 -encoding UTF-8 -cp "$CP:classes-common:classes-core" -d classes-scp @scp.list

find sshd-sftp/src/main/java -name '*.java' > sftp.list
test "$(wc -l < sftp.list)" -eq 126
mkdir -p classes-sftp
javac --release 8 -encoding UTF-8 -cp "$CP:classes-common:classes-core" -d classes-sftp @sftp.list
cp -a sshd-sftp/src/main/filtered-resources/. classes-sftp/

mkdir -p classes-osgi
cp -a classes-common/. classes-osgi/
cp -a classes-core/. classes-osgi/

pack_jar() {
	local jarname="$1" classes="$2" module="$3" sample="$4"
	cat > "$jarname.mf" << EOF
Manifest-Version: 1.0
Automatic-Module-Name: ${module}

EOF
	jar cfm "$jarname.jar" "$jarname.mf" -C "$classes" .
	jar i "$jarname.jar"
	javap -verbose -cp "$jarname.jar" "$sample" | grep -F 'major version: 52'
	jar --describe-module --file "$jarname.jar" > "$jarname.desc"
	if grep -F -q 'Unable to derive' "$jarname.desc"; then
		cat "$jarname.desc"
		exit 1
	fi
	grep -F -q "$module" "$jarname.desc"
	if jar tf "$jarname.jar" | grep -E '\.(java|jar|so|node|wasm)$'; then
		exit 1
	fi
}

pack_jar sshd-common classes-common org.apache.sshd.common org.apache.sshd.common.config.VersionProperties
pack_jar sshd-core classes-core org.apache.sshd.core org.apache.sshd.client.SshClient
pack_jar sshd-scp classes-scp org.apache.sshd.scp org.apache.sshd.scp.server.ScpCommandFactory
pack_jar sshd-sftp classes-sftp org.apache.sshd.sftp org.apache.sshd.sftp.server.SftpSubsystemFactory
pack_jar sshd-osgi classes-osgi org.apache.sshd.osgi org.apache.sshd.client.SshClient

jar tf sshd-common.jar | grep -F -q 'org/apache/sshd/sshd-version.properties'
jar tf sshd-osgi.jar | grep -F -q 'org/apache/sshd/client/SshClient.class'
jar tf sshd-osgi.jar | grep -F -q 'org/apache/sshd/common/config/VersionProperties.class'
if jar tf sshd-core.jar | grep -F -q 'agent/unix/'; then
	echo 'unix agent classes leaked into sshd-core'
	exit 1
fi
if jar tf sshd-osgi.jar | grep -F -q 'org/apache/sshd/scp/'; then
	echo 'scp classes leaked into sshd-osgi'
	exit 1
fi
if jar tf sshd-osgi.jar | grep -F -q 'org/apache/sshd/sftp/'; then
	echo 'sftp classes leaked into sshd-osgi'
	exit 1
fi

cat > sshd-common.pom << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.sshd</groupId>
  <artifactId>sshd-common</artifactId>
  <version>2.15.0</version>
  <name>Apache Mina SSHD :: Common</name>
  <description>Shared utilities for Apache MINA SSHD</description>
  <url>https://github.com/apache/mina-sshd</url>
  <licenses>
    <license>
      <name>Apache License, Version 2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
      <version>2.0.17</version>
    </dependency>
    <dependency>
      <groupId>org.bouncycastle</groupId>
      <artifactId>bcprov-jdk18on</artifactId>
      <version>1.86</version>
    </dependency>
    <dependency>
      <groupId>org.bouncycastle</groupId>
      <artifactId>bcpkix-jdk18on</artifactId>
      <version>1.86</version>
    </dependency>
    <dependency>
      <groupId>net.i2p.crypto</groupId>
      <artifactId>eddsa</artifactId>
      <version>0.3.0</version>
    </dependency>
  </dependencies>
</project>
EOF
cat > sshd-core.pom << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.sshd</groupId>
  <artifactId>sshd-core</artifactId>
  <version>2.15.0</version>
  <name>Apache Mina SSHD :: Core</name>
  <description>SSH client and server core for Apache MINA SSHD</description>
  <url>https://github.com/apache/mina-sshd</url>
  <licenses>
    <license>
      <name>Apache License, Version 2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.apache.sshd</groupId>
      <artifactId>sshd-common</artifactId>
      <version>2.15.0</version>
    </dependency>
  </dependencies>
</project>
EOF
cat > sshd-scp.pom << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.sshd</groupId>
  <artifactId>sshd-scp</artifactId>
  <version>2.15.0</version>
  <name>Apache Mina SSHD :: SCP</name>
  <description>SCP support for Apache MINA SSHD</description>
  <url>https://github.com/apache/mina-sshd</url>
  <licenses>
    <license>
      <name>Apache License, Version 2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.apache.sshd</groupId>
      <artifactId>sshd-core</artifactId>
      <version>2.15.0</version>
    </dependency>
  </dependencies>
</project>
EOF
cat > sshd-sftp.pom << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.sshd</groupId>
  <artifactId>sshd-sftp</artifactId>
  <version>2.15.0</version>
  <name>Apache Mina SSHD :: SFTP</name>
  <description>SFTP support for Apache MINA SSHD</description>
  <url>https://github.com/apache/mina-sshd</url>
  <licenses>
    <license>
      <name>Apache License, Version 2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.apache.sshd</groupId>
      <artifactId>sshd-core</artifactId>
      <version>2.15.0</version>
    </dependency>
  </dependencies>
</project>
EOF
cat > sshd-osgi.pom << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.sshd</groupId>
  <artifactId>sshd-osgi</artifactId>
  <version>2.15.0</version>
  <name>Apache Mina SSHD :: OSGi</name>
  <description>OSGi bundle of Apache MINA SSHD common and core</description>
  <url>https://github.com/apache/mina-sshd</url>
  <licenses>
    <license>
      <name>Apache License, Version 2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
      <version>2.0.17</version>
    </dependency>
    <dependency>
      <groupId>org.bouncycastle</groupId>
      <artifactId>bcprov-jdk18on</artifactId>
      <version>1.86</version>
    </dependency>
    <dependency>
      <groupId>org.bouncycastle</groupId>
      <artifactId>bcpkix-jdk18on</artifactId>
      <version>1.86</version>
    </dependency>
    <dependency>
      <groupId>net.i2p.crypto</groupId>
      <artifactId>eddsa</artifactId>
      <version>0.3.0</version>
    </dependency>
  </dependencies>
</project>
EOF

%install
sysjar install --buildroot %{buildroot} \
	--artifact sshd-common.pom:sshd-common.jar \
	--file-name sshd-common \
	--filelist .mfiles
sysjar install --buildroot %{buildroot} \
	--artifact sshd-core.pom:sshd-core.jar \
	--file-name sshd-core \
	--filelist .mfiles-core
sysjar install --buildroot %{buildroot} \
	--artifact sshd-scp.pom:sshd-scp.jar \
	--file-name sshd-scp \
	--filelist .mfiles-scp
sysjar install --buildroot %{buildroot} \
	--artifact sshd-sftp.pom:sshd-sftp.jar \
	--file-name sshd-sftp \
	--filelist .mfiles-sftp
sysjar install --buildroot %{buildroot} \
	--artifact sshd-osgi.pom:sshd-osgi.jar \
	--file-name sshd-osgi \
	--filelist .mfiles-osgi
for extra in core scp sftp osgi; do
	while IFS= read -r line; do
		grep -qxF "$line" .mfiles || printf '%s\n' "$line" >> .mfiles
	done < ".mfiles-$extra"
done

%check
set -eo pipefail
COMMON=%{buildroot}%{_javadir}/sshd-common.jar
CORE=%{buildroot}%{_javadir}/sshd-core.jar
SCP=%{buildroot}%{_javadir}/sshd-scp.jar
SFTP=%{buildroot}%{_javadir}/sshd-sftp.jar
test -f "$COMMON"
test -f "$CORE"
test -f "$SCP"
test -f "$SFTP"
test -f %{buildroot}%{_javadir}/sshd-osgi.jar
mkdir -p check
cat > check/Smoke.java << 'EOF'
import org.apache.sshd.client.SshClient;
import org.apache.sshd.common.config.VersionProperties;
import org.apache.sshd.scp.server.ScpCommandFactory;
import org.apache.sshd.sftp.server.SftpSubsystemFactory;
public class Smoke {
	public static void main(String[] args) throws Exception {
		SshClient client = SshClient.setUpDefaultClient();
		SftpSubsystemFactory sftp = new SftpSubsystemFactory();
		ScpCommandFactory scp = new ScpCommandFactory();
		String version = VersionProperties.getVersionProperties().get("sshd-version");
		System.out.println("sshd_ok " + version + " " + client.getClass().getSimpleName() + " " + (client.isStarted() ? "started" : "stopped"));
		System.out.println("sshd_factories " + sftp.getName() + " " + scp.getClass().getSimpleName() + " " + ScpCommandFactory.SCP_FACTORY_NAME);
		client.close();
	}
}
EOF
CP="$COMMON:$CORE:$SCP:$SFTP:%{_javadir}/slf4j-api.jar:%{_javadir}/eddsa.jar:%{_javadir}/bcprov-jdk18on.jar:%{_javadir}/bcpkix-jdk18on.jar:%{_javadir}/bcutil-jdk18on.jar"
javac --release 8 -encoding UTF-8 -cp "$CP" -d check check/Smoke.java
java -cp "check:$CP" Smoke > check/check.log
cat check/check.log
grep -F -q 'sshd_ok apache-sshd-%{version} SshClient stopped' check/check.log
grep -F -q 'sshd_factories sftp ScpCommandFactory scp' check/check.log

%files -f .mfiles
%license LICENSE.txt NOTICE.txt
%doc README.md CHANGES.md

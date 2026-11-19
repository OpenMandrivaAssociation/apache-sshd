Name:		apache-sshd
Version:	2.20.1
Release:	1
Summary:	Apache MINA SSHD
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/apache/mina-sshd
# Tag sshd-2.20.1. Last stable 2.x. 3.0.0 is still a milestone.
Source0:	https://github.com/apache/mina-sshd/archive/refs/tags/sshd-%{version}.tar.gz#/apache-sshd-%{version}.tar.gz
# Gradle 9.9.1 strictly pins sshd-core, sshd-osgi, sshd-scp, and sshd-sftp at 2.15.0.
Source1:	https://github.com/apache/mina-sshd/archive/refs/tags/sshd-2.15.0.tar.gz#/apache-sshd-2.15.0.tar.gz
# tomcat-apr 5.5 JNI is not packaged. The NIO local agent is the upstream fallback.
Patch0:		apache-sshd-2.15.0-no-apr.patch
# Bouncy Castle 1.86 moved ML-KEM out of org.bouncycastle.pqc.crypto.mlkem.
# 2.20.1 already imports the new packages. 2.15.0 still needs this patch.
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
Apache MINA SSHD %{version} is the pure Java SSH library.
This package builds sshd-common, sshd-core, sshd-scp, sshd-sftp, and the
sshd-osgi bundle (common plus core) from source. Gradle 9.9.1 strictly
pins 2.15.0, so those jars are installed beside %{version}.

%prep
%autosetup -n mina-sshd-sshd-%{version} -N -p1
patch -p1 -i %{_sourcedir}/apache-sshd-2.15.0-no-apr.patch
tar -xf %{SOURCE1}
patch -p1 -d mina-sshd-sshd-2.15.0 -i %{_sourcedir}/apache-sshd-2.15.0-no-apr.patch
patch -p1 -d mina-sshd-sshd-2.15.0 -i %{_sourcedir}/apache-sshd-2.15.0-mlkem.patch
find . \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -delete

%build
set -eo pipefail
CP="%{_javadir}/slf4j-api.jar:%{_javadir}/eddsa.jar:%{_javadir}/bcprov-jdk18on.jar:%{_javadir}/bcpkix-jdk18on.jar:%{_javadir}/bcutil-jdk18on.jar"

pack_jar() {
	jarname="$1"
	classes="$2"
	module="$3"
	sample="$4"
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

write_poms() {
	ver="$1"
	dir="$2"
	cat > "$dir/sshd-common.pom" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.sshd</groupId>
  <artifactId>sshd-common</artifactId>
  <version>$ver</version>
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
	cat > "$dir/sshd-core.pom" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.sshd</groupId>
  <artifactId>sshd-core</artifactId>
  <version>$ver</version>
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
      <version>$ver</version>
    </dependency>
  </dependencies>
</project>
EOF
	cat > "$dir/sshd-scp.pom" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.sshd</groupId>
  <artifactId>sshd-scp</artifactId>
  <version>$ver</version>
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
      <version>$ver</version>
    </dependency>
  </dependencies>
</project>
EOF
	cat > "$dir/sshd-sftp.pom" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.sshd</groupId>
  <artifactId>sshd-sftp</artifactId>
  <version>$ver</version>
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
      <version>$ver</version>
    </dependency>
  </dependencies>
</project>
EOF
	cat > "$dir/sshd-osgi.pom" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.sshd</groupId>
  <artifactId>sshd-osgi</artifactId>
  <version>$ver</version>
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
}

build_tree() {
	root="$1"
	ver="$2"
	ncommon="$3"
	ncore="$4"
	nscp="$5"
	nsftp="$6"
	dest="$7"
	mkdir -p "$dest"
	find "$root/sshd-common/src/main/java" -name '*.java' > "$dest/common.list"
	test "$(wc -l < "$dest/common.list")" -eq "$ncommon"
	mkdir -p "$dest/classes-common"
	javac --release 8 -encoding UTF-8 -cp "$CP" -d "$dest/classes-common" @"$dest/common.list"
	cp -a "$root/sshd-common/src/main/filtered-resources/." "$dest/classes-common/"
	cat > "$dest/classes-common/org/apache/sshd/sshd-version.properties" << EOF
groupId=org.apache.sshd
artifactId=sshd-common
version=$ver
sshd-version=apache-sshd-$ver
EOF

	find "$root/sshd-core/src/main/java" -name '*.java' ! -path '*/agent/unix/*' > "$dest/core.list"
	test "$(wc -l < "$dest/core.list")" -eq "$ncore"
	test "$(find "$root/sshd-core/src/main/java" -path '*/agent/unix/*.java' | wc -l)" -eq 8
	mkdir -p "$dest/classes-core"
	javac --release 8 -encoding UTF-8 -cp "$CP:$dest/classes-common" -d "$dest/classes-core" @"$dest/core.list"
	cp -a "$root/sshd-core/src/main/filtered-resources/." "$dest/classes-core/"

	find "$root/sshd-scp/src/main/java" -name '*.java' > "$dest/scp.list"
	test "$(wc -l < "$dest/scp.list")" -eq "$nscp"
	mkdir -p "$dest/classes-scp"
	javac --release 8 -encoding UTF-8 -cp "$CP:$dest/classes-common:$dest/classes-core" -d "$dest/classes-scp" @"$dest/scp.list"

	find "$root/sshd-sftp/src/main/java" -name '*.java' > "$dest/sftp.list"
	test "$(wc -l < "$dest/sftp.list")" -eq "$nsftp"
	mkdir -p "$dest/classes-sftp"
	javac --release 8 -encoding UTF-8 -cp "$CP:$dest/classes-common:$dest/classes-core" -d "$dest/classes-sftp" @"$dest/sftp.list"
	cp -a "$root/sshd-sftp/src/main/filtered-resources/." "$dest/classes-sftp/"

	mkdir -p "$dest/classes-osgi"
	cp -a "$dest/classes-common/." "$dest/classes-osgi/"
	cp -a "$dest/classes-core/." "$dest/classes-osgi/"

	pack_jar "$dest/sshd-common" "$dest/classes-common" org.apache.sshd.common org.apache.sshd.common.config.VersionProperties
	pack_jar "$dest/sshd-core" "$dest/classes-core" org.apache.sshd.core org.apache.sshd.client.SshClient
	pack_jar "$dest/sshd-scp" "$dest/classes-scp" org.apache.sshd.scp org.apache.sshd.scp.server.ScpCommandFactory
	pack_jar "$dest/sshd-sftp" "$dest/classes-sftp" org.apache.sshd.sftp org.apache.sshd.sftp.server.SftpSubsystemFactory
	pack_jar "$dest/sshd-osgi" "$dest/classes-osgi" org.apache.sshd.osgi org.apache.sshd.client.SshClient
	write_poms "$ver" "$dest"

	jar tf "$dest/sshd-common.jar" | grep -F -q 'org/apache/sshd/sshd-version.properties'
	jar tf "$dest/sshd-osgi.jar" | grep -F -q 'org/apache/sshd/client/SshClient.class'
	jar tf "$dest/sshd-osgi.jar" | grep -F -q 'org/apache/sshd/common/config/VersionProperties.class'
	if jar tf "$dest/sshd-core.jar" | grep -F -q 'agent/unix/'; then
		echo 'unix agent classes leaked into sshd-core'
		exit 1
	fi
	if jar tf "$dest/sshd-osgi.jar" | grep -F -q 'org/apache/sshd/scp/'; then
		echo 'scp classes leaked into sshd-osgi'
		exit 1
	fi
	if jar tf "$dest/sshd-osgi.jar" | grep -F -q 'org/apache/sshd/sftp/'; then
		echo 'sftp classes leaked into sshd-osgi'
		exit 1
	fi
	grep -F -q "version=$ver" "$dest/classes-common/org/apache/sshd/sshd-version.properties"
}

build_tree . %{version} 408 356 39 128 out
build_tree mina-sshd-sshd-2.15.0 2.15.0 406 356 39 126 out215

%install
set -eo pipefail
for art in common core scp sftp osgi; do
	sysjar install --buildroot %{buildroot} \
		--artifact "out215/sshd-$art.pom:out215/sshd-$art.jar" \
		--file-name "sshd-$art-2.15.0" \
		--filelist ".mfiles215-$art"
	/bin/mv "%{buildroot}/usr/share/sysjar/index/org.apache.sshd/sshd-$art.sysjar" \
		"%{buildroot}/usr/share/sysjar/index/org.apache.sshd/sshd-$art-2.15.0.sysjar"
	sed -i "s|/usr/share/sysjar/index/org.apache.sshd/sshd-$art\\.sysjar|/usr/share/sysjar/index/org.apache.sshd/sshd-$art-2.15.0.sysjar|" ".mfiles215-$art"
	idx215="%{buildroot}/usr/share/sysjar/index/org.apache.sshd/sshd-$art-2.15.0.sysjar"
	test -s "$idx215"
	grep -F -q '"version": "2.15.0"' "$idx215"
	grep -F -q "\"artifactId\": \"sshd-$art\"" "$idx215"
done
for art in common core scp sftp osgi; do
	sysjar install --buildroot %{buildroot} \
		--artifact "out/sshd-$art.pom:out/sshd-$art.jar" \
		--file-name "sshd-$art" \
		--filelist ".mfiles-$art"
	idx="%{buildroot}/usr/share/sysjar/index/org.apache.sshd/sshd-$art.sysjar"
	test -s "$idx"
	grep -F -q '"version": "%{version}"' "$idx"
	grep -F -q "\"artifactId\": \"sshd-$art\"" "$idx"
	test -s "%{buildroot}%{_javadir}/sshd-$art.jar"
	test -s "%{buildroot}%{_javadir}/sshd-$art-2.15.0.jar"
done
: > .mfiles
for art in common core scp sftp osgi; do
	while IFS= read -r line; do
		grep -qxF -- "$line" .mfiles || printf '%s\n' "$line" >> .mfiles
	done < ".mfiles-$art"
	while IFS= read -r line; do
		grep -qxF -- "$line" .mfiles || printf '%s\n' "$line" >> .mfiles
	done < ".mfiles215-$art"
done

%check
set -eo pipefail
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
DEPS="%{_javadir}/slf4j-api.jar:%{_javadir}/eddsa.jar:%{_javadir}/bcprov-jdk18on.jar:%{_javadir}/bcpkix-jdk18on.jar:%{_javadir}/bcutil-jdk18on.jar"
run_check() {
	label="$1"
	ver="$2"
	common="$3"
	core="$4"
	scp="$5"
	sftp="$6"
	cp="$common:$core:$scp:$sftp:$DEPS"
	mkdir -p "check/$label"
	javac --release 8 -encoding UTF-8 -cp "$cp" -d "check/$label" check/Smoke.java
	java -cp "check/$label:$cp" Smoke > "check/$label.log"
	cat "check/$label.log"
	grep -F -q "sshd_ok apache-sshd-$ver SshClient stopped" "check/$label.log"
	grep -F -q 'sshd_factories sftp ScpCommandFactory scp' "check/$label.log"
}
run_check new %{version} \
	%{buildroot}%{_javadir}/sshd-common.jar \
	%{buildroot}%{_javadir}/sshd-core.jar \
	%{buildroot}%{_javadir}/sshd-scp.jar \
	%{buildroot}%{_javadir}/sshd-sftp.jar
run_check old 2.15.0 \
	%{buildroot}%{_javadir}/sshd-common-2.15.0.jar \
	%{buildroot}%{_javadir}/sshd-core-2.15.0.jar \
	%{buildroot}%{_javadir}/sshd-scp-2.15.0.jar \
	%{buildroot}%{_javadir}/sshd-sftp-2.15.0.jar

%files -f .mfiles
%license LICENSE.txt NOTICE.txt
%doc README.md CHANGES.md

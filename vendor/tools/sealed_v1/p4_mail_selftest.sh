#!/usr/bin/env bash
set -eu
task_tool_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
task_test_dir=$(mktemp -d)
trap 'rm -rf -- "$task_test_dir"' EXIT
umask 077
mkdir "$task_test_dir/pubs"
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out "$task_test_dir/key.pem" 2>"$task_test_dir/key.log"
openssl pkey -in "$task_test_dir/key.pem" -pubout -out "$task_test_dir/pub.pem"
for task_seat in 1 2 3 4 5 6 7 8; do
    cp "$task_test_dir/pub.pem" "$task_test_dir/pubs/p${task_seat}.pem"
done
task_mail() { perl "$task_tool_dir/p4_mail_v1.pl" "$@"; }
task_bad() {
    if "$@" >"$task_test_dir/rejected.log" 2>&1; then
        printf '%s\n' 'FAIL: invalid input was accepted' >&2
        exit 1
    fi
}
task_list_commit=$(task_mail init selftest 1 1,2,3,4,8 "$task_test_dir/list-state.json")
task_pad_commit=$(task_mail init selftest 1 none "$task_test_dir/pad-state.json")
task_mail offer "$task_test_dir/list-state.json" "$task_test_dir/key.pem" "$task_test_dir/pubs" "$task_test_dir/list-offer.json"
task_mail offer "$task_test_dir/pad-state.json" "$task_test_dir/key.pem" "$task_test_dir/pubs" "$task_test_dir/pad-offer.json"
task_mail receive selftest 1 4 "$task_list_commit" "$task_test_dir/key.pem" "$task_test_dir/pub.pem" "$task_test_dir/list-offer.json" "$task_test_dir/list-body.json"
task_mail check selftest 1 4 "$task_list_commit" "$task_test_dir/list-body.json"
task_mail receive selftest 1 4 "$task_pad_commit" "$task_test_dir/key.pem" "$task_test_dir/pub.pem" "$task_test_dir/pad-offer.json" "$task_test_dir/pad-body.json"
task_mail check selftest 1 4 "$task_pad_commit" "$task_test_dir/pad-body.json"
task_mail receive selftest 1 6 "$task_list_commit" "$task_test_dir/key.pem" "$task_test_dir/pub.pem" "$task_test_dir/list-offer.json" "$task_test_dir/outside-body.json"
task_mail check selftest 1 6 "$task_list_commit" "$task_test_dir/outside-body.json"
perl -MJSON::PP -e '
    local $/; open my $a,"<",$ARGV[0] or die; my $x=<$a>;
    open my $b,"<",$ARGV[1] or die; my $y=<$b>;
    die "packet sizes differ" unless length($x)==length($y);
    my $p=decode_json($x); my $q=decode_json($y);
    for my $e (@{$p->{envelopes}},@{$q->{envelopes}}) {
        die unless length($e->{ciphertext})==512 && length($e->{signature})==512;
    }
    my ($e)=grep {$_->{to}==4} @{$p->{envelopes}};
    open my $o,">",$ARGV[2] or die; print {$o} JSON::PP->new->canonical->encode($e); close $o;
    substr($e->{ciphertext},0,1,substr($e->{ciphertext},0,1) eq "A" ? "B":"A");
    open my $t,">",$ARGV[3] or die; print {$t} JSON::PP->new->canonical->encode($e); close $t;
' "$task_test_dir/list-offer.json" "$task_test_dir/pad-offer.json" "$task_test_dir/envelope.json" "$task_test_dir/tampered.json"
task_bad task_mail open selftest offer 1 4 "$task_list_commit" "$task_test_dir/key.pem" "$task_test_dir/pub.pem" "$task_test_dir/tampered.json" "$task_test_dir/bad-output.json"
task_bad task_mail open othergame offer 1 4 "$task_list_commit" "$task_test_dir/key.pem" "$task_test_dir/pub.pem" "$task_test_dir/envelope.json" "$task_test_dir/bad-output.json"
task_bad task_mail open selftest confirm 1 4 "$task_list_commit" "$task_test_dir/key.pem" "$task_test_dir/pub.pem" "$task_test_dir/envelope.json" "$task_test_dir/bad-output.json"
task_bad task_mail open selftest offer 1 5 "$task_list_commit" "$task_test_dir/key.pem" "$task_test_dir/pub.pem" "$task_test_dir/envelope.json" "$task_test_dir/bad-output.json"
task_bad task_mail check selftest 1 4 "$task_pad_commit" "$task_test_dir/list-body.json"
task_bad task_mail check selftest 1 6 "$task_list_commit" "$task_test_dir/list-body.json"
task_bad task_mail init selftest 1 1,2,3,4,8 "$task_test_dir/list-state.json"
task_bad task_mail init selftest 1 1,1,2,3,4 "$task_test_dir/invalid-state.json"
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out "$task_test_dir/wrong-key.pem" 2>"$task_test_dir/wrong-key.log"
openssl pkey -in "$task_test_dir/wrong-key.pem" -pubout -out "$task_test_dir/wrong-pub.pem"
task_bad task_mail open selftest offer 1 4 "$task_list_commit" "$task_test_dir/key.pem" "$task_test_dir/wrong-pub.pem" "$task_test_dir/envelope.json" "$task_test_dir/bad-output.json"
task_bad task_mail open selftest offer 1 4 "$task_list_commit" "$task_test_dir/wrong-key.pem" "$task_test_dir/pub.pem" "$task_test_dir/envelope.json" "$task_test_dir/bad-output.json"
test ! -e "$task_test_dir/bad-output.json"
printf '%s\n' 'PASS: round trip, fixed sizes, padding isolation, signature tampering, game/phase/recipient binding, commitment validation, wrong keys, exclusive output creation'

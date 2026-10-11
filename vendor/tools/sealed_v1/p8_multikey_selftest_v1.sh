#!/usr/bin/env bash
# Disposable test keys only; never reads a player's credential or game state.
# Usage: bash p8_multikey_selftest_v1.sh /absolute/path/p4_mail_v1.pl
set -eu
test "$#" -eq 1 || { printf '%s\n' 'usage: bash p8_multikey_selftest_v1.sh MAIL_TOOL' >&2; exit 2; }
task_mail_tool=$1
test -f "$task_mail_tool"
task_dir=$(mktemp -d)
trap 'rm -rf -- "$task_dir"' EXIT
umask 077
mkdir "$task_dir/pubs"
for task_seat in 1 2 3 4 5 6 7 8; do
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 \
        -out "$task_dir/key$task_seat.pem" 2>"$task_dir/key$task_seat.log"
    openssl pkey -in "$task_dir/key$task_seat.pem" -pubout \
        -out "$task_dir/pubs/p$task_seat.pem"
done
task_mail() { perl "$task_mail_tool" "$@"; }
task_reject() {
    if "$@" >"$task_dir/rejection.log" 2>&1; then
        printf '%s\n' 'FAIL: invalid operation accepted' >&2
        exit 1
    fi
}
task_c=$(task_mail init p8-multikey-test 1 1,2,3,4,8 "$task_dir/state.json")
task_pad_c=$(task_mail init p8-multikey-test 1 none "$task_dir/pad-state.json")
task_mail offer "$task_dir/state.json" "$task_dir/key1.pem" "$task_dir/pubs" \
    "$task_dir/offer.json" >"$task_dir/offer.log"
task_mail offer "$task_dir/pad-state.json" "$task_dir/key1.pem" "$task_dir/pubs" \
    "$task_dir/pad-offer.json" >"$task_dir/pad-offer.log"
for task_seat in 2 3 4 5 6 7 8; do
    task_mail receive p8-multikey-test 1 "$task_seat" "$task_c" \
        "$task_dir/key$task_seat.pem" "$task_dir/pubs/p1.pem" \
        "$task_dir/offer.json" "$task_dir/body$task_seat.json" >"$task_dir/receive.log"
    task_result=$(task_mail check p8-multikey-test 1 "$task_seat" "$task_c" \
        "$task_dir/body$task_seat.json")
    case "$task_seat" in
        2|3|4|8) test "$task_result" = 'valid list' ;;
        *) test "$task_result" = 'padding' ;;
    esac
done
# A packet with distinct recipient keys must reject another recipient's key.
task_reject task_mail receive p8-multikey-test 1 2 "$task_c" \
    "$task_dir/key3.pem" "$task_dir/pubs/p1.pem" "$task_dir/offer.json" "$task_dir/rejected.json"
# Sender authentication must reject a different registered sender public key.
task_reject task_mail receive p8-multikey-test 1 2 "$task_c" \
    "$task_dir/key2.pem" "$task_dir/pubs/p2.pem" "$task_dir/offer.json" "$task_dir/rejected.json"
# Even a correctly signed envelope can be encrypted to the wrong key.
task_mail seal p8-multikey-test offer 1 2 "$task_c" "$task_dir/key1.pem" \
    "$task_dir/pubs/p3.pem" "$task_dir/body2.json" "$task_dir/wrong-recipient-key.json" \
    >"$task_dir/seal.log"
task_reject task_mail open p8-multikey-test offer 1 2 "$task_c" \
    "$task_dir/key2.pem" "$task_dir/pubs/p1.pem" \
    "$task_dir/wrong-recipient-key.json" "$task_dir/rejected.json"
test ! -e "$task_dir/rejected.json"
perl -MJSON::PP -e '
    local $/;
    open my $a,"<",$ARGV[0] or die; my $x=<$a>;
    open my $b,"<",$ARGV[1] or die; my $y=<$b>;
    die "different public packet sizes" unless length($x)==length($y);
    my $p=decode_json($x);
    for my $s (5,6,7) {
        open my $f,"<","$ARGV[2]/body$s.json" or die;
        my $body=decode_json(<$f>);
        die "padding exposes fields" unless join(",",sort keys %$body) eq "pad" && $body->{pad}==1;
    }
    for my $e (@{$p->{envelopes}}) {
        die "nonfixed envelope" unless length($e->{ciphertext})==512 && length($e->{signature})==512;
    }
' "$task_dir/offer.json" "$task_dir/pad-offer.json" "$task_dir"
printf '%s\n' 'PASS: eight distinct keys, seven recipient checks, sender/recipient isolation, signed wrong-key rejection, equal packet sizes, padding field isolation'

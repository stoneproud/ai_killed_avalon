#!/usr/bin/env perl
use strict;
use warnings;
use JSON::PP;
use Digest::SHA qw(sha256_hex);
use MIME::Base64 qw(encode_base64 decode_base64);
use File::Temp qw(tempdir);
use Fcntl qw(O_WRONLY O_CREAT O_EXCL);

# Local, opt-in file utility. No network, Git, role discovery or automatic moves.
# Private inputs and decrypted outputs belong outside the public repository.
umask 0077;
my $json = JSON::PP->new->canonical(1)->ascii(1);
my $dir = tempdir('av8-mail-XXXXXX', TMPDIR => 1, CLEANUP => 1);
my $serial = 0;
sub tmp { return "$dir/" . ++$serial; }
sub fail { die "mail-v1: $_[0]\n"; }
sub read_file {
    my ($p) = @_;
    open my $f, '<:raw', $p or fail("cannot read $p: $!");
    my $s = do { local $/; <$f> } // '';
    close $f or fail('read close failed');
    length($s) <= 1048576 or fail('input exceeds 1 MiB');
    return $s;
}
sub write_new {
    my ($p, $s) = @_;
    sysopen my $f, $p, O_WRONLY | O_CREAT | O_EXCL, 0600
        or fail("cannot create new file $p: $!");
    binmode $f;
    print {$f} $s or fail('write failed');
    close $f or fail('write close failed');
}
sub decode {
    my ($s) = @_;
    my $v = eval { $json->decode($s) };
    $@ and fail('invalid JSON');
    ref($v) eq 'HASH' or fail('JSON object required');
    return $v;
}
sub fields {
    my ($v, @names) = @_;
    join(',', sort keys %$v) eq join(',', sort @names)
        or fail('unexpected or missing fields');
}
sub token {
    defined($_[0]) && !ref($_[0]) && $_[0] =~ /\A[A-Za-z0-9_-]{1,32}\z/
        or fail('invalid game or phase');
    return $_[0];
}
sub seat {
    defined($_[0]) && !ref($_[0]) && $_[0] =~ /\A[1-8]\z/
        or fail('invalid seat');
    return 0 + $_[0];
}
sub hex64 {
    defined($_[0]) && !ref($_[0]) && $_[0] =~ /\A[0-9a-f]{64}\z/
        or fail('expected 32 bytes in lowercase hex');
    return $_[0];
}
sub random_bytes {
    my ($n) = @_;
    my $p = tmp();
    system('openssl', 'rand', '-out', $p, $n) == 0 or fail('random generation failed');
    my $s = read_file($p);
    length($s) == $n or fail('short randomness');
    return $s;
}
sub list_value {
    my ($l) = @_;
    return 'none' if !defined($l);
    ref($l) eq 'ARRAY' && @$l == 5 or fail('list must contain five seats');
    my @s = map { seat($_) } @$l;
    my %u = map { $_ => 1 } @s;
    keys(%u) == 5 or fail('duplicate seats');
    join(',', @s) eq join(',', sort { $a <=> $b } @s)
        or fail('list must be in increasing order');
    return join(',', @s);
}
sub has_seat { my ($l, $s) = @_; return defined($l) && scalar(grep { $_ == $s } @$l); }
sub commitment {
    my ($g, $s, $l, $n) = @_;
    return sha256_hex(join("\0", 'av8-mail-v1-commit', token($g), seat($s), list_value($l), hex64($n)));
}
sub state {
    my ($p) = @_;
    my $v = decode(read_file($p));
    fields($v, qw(v game sender list nonce commitment));
    $v->{v} == 1 or fail('unknown state version');
    token($v->{game}); seat($v->{sender}); list_value($v->{list});
    !defined($v->{list}) || has_seat($v->{list}, $v->{sender})
        or fail('sender is absent from own list');
    commitment(@$v{qw(game sender list nonce)}) eq $v->{commitment}
        or fail('state commitment mismatch');
    return $v;
}
sub signed_text { return "av8-mail-v1-envelope\n" . $json->encode($_[0]) . "\n"; }
sub seal {
    my ($g, $phase, $from, $to, $c, $key, $pub, $body) = @_;
    token($g); token($phase); seat($from); seat($to); hex64($c);
    length($body) <= 246 or fail('body exceeds 246 bytes');
    decode($body);
    my $plain = tmp(); my $cipher = tmp(); my $signed = tmp(); my $sig = tmp();
    write_new($plain, "AV8M1\0\0\0" . pack('n', length($body)) . $body . random_bytes(246-length($body)));
    system('openssl', 'pkeyutl', '-encrypt', '-pubin', '-inkey', $pub,
        '-pkeyopt', 'rsa_padding_mode:oaep', '-pkeyopt', 'rsa_oaep_md:sha256',
        '-pkeyopt', 'rsa_mgf1_md:sha256', '-in', $plain, '-out', $cipher) == 0
        or fail('encryption failed');
    my $ct = read_file($cipher);
    length($ct) == 384 or fail('only RSA-3072 keys supported');
    my $e = { v => 1, game => $g, phase => $phase, from => 0+$from, to => 0+$to,
        commitment => $c, ciphertext => encode_base64($ct, '') };
    write_new($signed, signed_text($e));
    system('openssl', 'dgst', '-sha256', '-sign', $key, '-out', $sig, $signed) == 0
        or fail('signature failed');
    my $sb = read_file($sig);
    length($sb) == 384 or fail('only RSA-3072 signatures supported');
    $e->{signature} = encode_base64($sb, '');
    return $e;
}
sub open_envelope {
    my ($g, $phase, $from, $to, $c, $key, $pub, $e) = @_;
    token($g); token($phase); seat($from); seat($to); hex64($c);
    fields($e, qw(v game phase from to commitment ciphertext signature));
    $e->{v} == 1 && $e->{game} eq $g && $e->{phase} eq $phase
        && $e->{from} eq "$from" && $e->{to} eq "$to" && $e->{commitment} eq $c
        or fail('envelope context mismatch');
    for my $k (qw(ciphertext signature)) {
        defined($e->{$k}) && !ref($e->{$k}) && $e->{$k} =~ /\A[A-Za-z0-9+\/]{512}\z/
            or fail('invalid fixed-size encoding');
    }
    my %unsigned = %$e; delete $unsigned{signature};
    my $signed = tmp(); my $sig = tmp(); my $cipher = tmp(); my $plain = tmp();
    write_new($signed, signed_text(\%unsigned));
    write_new($sig, decode_base64($e->{signature}));
    system('openssl', 'dgst', '-sha256', '-verify', $pub, '-signature', $sig, $signed) == 0
        or fail('signature verification failed');
    write_new($cipher, decode_base64($e->{ciphertext}));
    system('openssl', 'pkeyutl', '-decrypt', '-inkey', $key,
        '-pkeyopt', 'rsa_padding_mode:oaep', '-pkeyopt', 'rsa_oaep_md:sha256',
        '-pkeyopt', 'rsa_mgf1_md:sha256', '-in', $cipher, '-out', $plain) == 0
        or fail('decryption failed');
    my $p = read_file($plain);
    length($p) == 256 && substr($p, 0, 8) eq "AV8M1\0\0\0" or fail('invalid plaintext frame');
    my $n = unpack('n', substr($p, 8, 2));
    $n <= 246 or fail('invalid body length');
    my $body = substr($p, 10, $n); decode($body);
    return $body;
}
sub usage {
    die <<'HELP';
Usage (run with perl; all output paths must be new):
  init GAME SEAT 1,2,3,4,8|none PRIVATE_STATE
  offer PRIVATE_STATE PRIVATE_KEY PUBLIC_PEM_DIR PUBLIC_PACKET
  receive GAME EXPECTED_SENDER MY_SEAT FIRST_COMMITMENT PRIVATE_KEY SENDER_PEM PACKET PRIVATE_BODY
  check GAME EXPECTED_SENDER MY_SEAT FIRST_COMMITMENT PRIVATE_BODY
  seal GAME PHASE FROM TO COMMITMENT PRIVATE_KEY RECIPIENT_PEM PRIVATE_BODY PUBLIC_ENVELOPE
  open GAME PHASE FROM TO COMMITMENT PRIVATE_KEY SENDER_PEM ENVELOPE PRIVATE_BODY
PEM directory must contain p1.pem ... p8.pem exported from host-registered SSH keys.
Private state, body and key files MUST NOT be published. Packet/envelope files may be published.
HELP
}
my $cmd = shift @ARGV // ''; my @a = @ARGV;
if ($cmd eq 'init' && @a == 4) {
    my ($g, $s, $value, $out) = @a; token($g); seat($s);
    my $l = $value eq 'none' ? undef : [split /,/, $value, -1];
    list_value($l);
    !defined($l) || has_seat($l, $s) or fail('list must include sender');
    $l = [map { 0+$_ } @$l] if defined($l);
    my $n = unpack('H*', random_bytes(32));
    my $c = commitment($g, $s, $l, $n);
    write_new($out, $json->encode({v=>1, game=>$g, sender=>0+$s, list=>$l, nonce=>$n, commitment=>$c})."\n");
    print "$c\n";
} elsif ($cmd eq 'offer' && @a == 4) {
    my ($sp, $key, $pubdir, $out) = @a; my $s = state($sp); my @env;
    for my $to (1..8) {
        next if $to == $s->{sender};
        my $body = has_seat($s->{list}, $to)
            ? {list=>$s->{list}, nonce=>$s->{nonce}} : {pad=>1};
        push @env, seal($s->{game}, 'offer', $s->{sender}, $to, $s->{commitment},
            $key, "$pubdir/p$to.pem", $json->encode($body));
    }
    write_new($out, $json->encode({v=>1, game=>$s->{game}, phase=>'offer', sender=>$s->{sender},
        commitment=>$s->{commitment}, envelopes=>\@env})."\n");
    print "offer packet created\n";
} elsif ($cmd eq 'receive' && @a == 8) {
    my ($g, $from, $to, $c, $key, $pub, $packet, $out) = @a;
    token($g); seat($from); seat($to); hex64($c); $from != $to or fail('self receipt uses private state');
    my $p = decode(read_file($packet)); fields($p, qw(v game phase sender commitment envelopes));
    $p->{v} == 1 && $p->{game} eq $g && $p->{phase} eq 'offer' && $p->{sender} eq "$from"
        && $p->{commitment} eq $c or fail('packet context mismatch');
    ref($p->{envelopes}) eq 'ARRAY' && @{$p->{envelopes}} == 7 or fail('seven envelopes required');
    my @recipients = grep { $_ != $from } 1..8;
    for my $i (0..6) {
        ref($p->{envelopes}[$i]) eq 'HASH' && $p->{envelopes}[$i]{to} eq "$recipients[$i]"
            or fail('recipients must be distinct and sorted');
    }
    my ($e) = grep { $_->{to} == $to } @{$p->{envelopes}};
    write_new($out, open_envelope($g, 'offer', $from, $to, $c, $key, $pub, $e)."\n");
    print "body saved privately\n";
} elsif ($cmd eq 'check' && @a == 5) {
    my ($g, $from, $to, $c, $body) = @a;
    token($g); seat($from); seat($to); hex64($c);
    my $b = decode(read_file($body));
    if (exists $b->{pad}) { fields($b, 'pad'); $b->{pad} == 1 or fail('invalid padding'); print "padding\n"; exit 0; }
    fields($b, qw(list nonce)); list_value($b->{list});
    has_seat($b->{list}, $from) && has_seat($b->{list}, $to) or fail('sender or recipient missing from list');
    commitment($g, $from, $b->{list}, $b->{nonce}) eq $c or fail('opening does not match first commitment');
    print "valid list\n";
} elsif ($cmd eq 'seal' && @a == 9) {
    my $out = pop @a; my $body_path = pop @a;
    write_new($out, $json->encode(seal(@a, read_file($body_path)))."\n");
    print "envelope created\n";
} elsif ($cmd eq 'open' && @a == 9) {
    my $out = pop @a; my $path = pop @a;
    write_new($out, open_envelope(@a, decode(read_file($path)))."\n");
    print "body saved privately\n";
} else { usage(); }

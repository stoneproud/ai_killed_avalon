#!/usr/bin/env perl
use strict;
use warnings;
use JSON::PP;
# Read-only public schema guard; no keys, network, Git, decryption or game actions.
# Does not authenticate reports, first windows, signatures, or list truth.
sub need { die "public-guard: $_[1]\n" unless $_[0] }
sub scalar_is { defined($_[0]) && !ref($_[0]) && $_[0] eq $_[1] }
sub seat_ok { defined($_[0]) && !ref($_[0]) && $_[0] =~ /\A[1-8]\z/ }
sub exact {
    my ($d,@f)=@_;
    need(ref($d) eq 'HASH','object required');
    need(join(',',sort keys %$d) eq join(',',sort @f),'unexpected or missing public fields');
}
sub five {
    my ($l)=@_;
    need(ref($l) eq 'ARRAY' && @$l==5,'five-seat array required');
    my $last=0;
    for (@$l) { need(seat_ok($_) && $_>$last,'five seats must be increasing and distinct'); $last=$_ }
    return join(',',@$l);
}
sub contains { my ($l,$s)=@_; scalar grep {$_==$s} @$l }
sub validate {
    my ($game,$seat,$d)=@_;
    need(defined($game) && $game =~ /\A[A-Za-z0-9_-]{1,32}\z/,'invalid expected game');
    need(seat_ok($seat),'invalid expected seat');
    need(ref($d) eq 'HASH' && scalar_is($d->{v},1) && scalar_is($d->{game},$game),'version/game mismatch');
    my $phase=$d->{phase}//'';
    if ($phase eq 'offer') {
        exact($d,qw(v game phase sender commitment envelopes));
        need(scalar_is($d->{sender},$seat),'sender mismatch');
        need(defined($d->{commitment}) && !ref($d->{commitment}) && $d->{commitment}=~/\A[0-9a-f]{64}\z/,'commitment format');
        need(ref($d->{envelopes}) eq 'ARRAY' && @{$d->{envelopes}}==7,'seven envelopes required');
        my @to=grep {$_!=$seat} 1..8;
        for my $i (0..6) {
            my $e=$d->{envelopes}[$i];
            exact($e,qw(v game phase from to commitment ciphertext signature));
            for my $pair ([v=>1],[game=>$game],[phase=>'offer'],[from=>$seat],[to=>$to[$i]],[commitment=>$d->{commitment}]) {
                need(scalar_is($e->{$pair->[0]},$pair->[1]),'envelope context mismatch');
            }
            for my $f (qw(ciphertext signature)) {
                need(defined($e->{$f}) && !ref($e->{$f}) && $e->{$f}=~/\A[A-Za-z0-9+\/]{512}\z/,'fixed-size encoding required');
            }
        }
    } elsif ($phase eq 'receipt') {
        exact($d,qw(v game phase seat lists four_choice));
        need(scalar_is($d->{seat},$seat),'seat mismatch');
        need(ref($d->{lists}) eq 'ARRAY' && @{$d->{lists}}<=4,'zero through four lists required');
        my ($prev,%seen)=('');
        for my $l (@{$d->{lists}}) {
            my $k=five($l);
            need(contains($l,$seat) && (!$prev || $k gt $prev),'receipt membership/order');
            $seen{$k}=1; $prev=$k;
        }
        need(ref($d->{four_choice}) eq 'ARRAY','four_choice array required');
        if (@{$d->{four_choice}}) {
            my $k=five($d->{four_choice});
            need(@{$d->{lists}}==4 && $seen{$k},'four_choice must be among four received lists');
        }
    } elsif ($phase eq 'x_source') {
        exact($d,qw(v game phase seat X source));
        need(scalar_is($d->{seat},$seat),'seat mismatch'); five($d->{X});
        # null is an explicit non-report, not an authenticated source.
        need(!defined($d->{source}) || (seat_ok($d->{source}) && contains($d->{X},$d->{source})),'source must belong to X');
        need(contains($d->{X},$seat) || !defined($d->{source}),'nonmember cannot report X source');
    } elsif ($phase eq 'x_choice') {
        exact($d,qw(v game phase seat X excluded_source choice));
        need(scalar_is($d->{seat},$seat),'seat mismatch'); five($d->{X}); five($d->{choice});
        need(!contains($d->{X},$seat) && contains($d->{choice},$seat),'choice membership');
        need(seat_ok($d->{excluded_source}) && contains($d->{X},$d->{excluded_source}),'excluded source membership');
    } else { die "public-guard: unknown phase\n" }
    return 1;
}
if (@ARGV==1 && $ARGV[0] eq '--self-test') {
    my $d={v=>1,game=>'guard-test',phase=>'receipt',seat=>6,lists=>[[1,2,3,4,6]],four_choice=>[]};
    validate('guard-test',6,$d);
    for my $extra (qw(nonce source verified private_state role)) {
        my %copy=(%$d,$extra=>'PRIVATE');
        need(!eval {validate('guard-test',6,\%copy);1},'private extra field accepted');
    }
    need(!eval {validate('another-game',6,$d);1},'wrong game accepted');
    need(!eval {validate('guard-test',5,$d);1},'wrong seat accepted');
    my %bad=(%$d,lists=>[[1,2,3,4,5]]);
    need(!eval {validate('guard-test',6,\%bad);1},'nonmember list accepted');
    my $source={v=>1,game=>'guard-test',phase=>'x_source',seat=>6,X=>[1,2,3,4,6],source=>3};
    validate('guard-test',6,$source);
    my $choice={v=>1,game=>'guard-test',phase=>'x_choice',seat=>6,X=>[1,2,3,4,5],excluded_source=>3,choice=>[1,2,3,4,6]};
    validate('guard-test',6,$choice);
    my $commit='a'x64;
    my $offer={v=>1,game=>'guard-test',phase=>'offer',sender=>6,commitment=>$commit,
        envelopes=>[map {{v=>1,game=>'guard-test',phase=>'offer',from=>6,to=>$_,
            commitment=>$commit,ciphertext=>'A'x512,signature=>'B'x512}} grep {$_!=6} 1..8]};
    validate('guard-test',6,$offer); # Synthetic structure; intentionally not a signed packet.
    $offer->{envelopes}[0]{to}=6;
    need(!eval {validate('guard-test',6,$offer);1},'wrong envelope recipient accepted');
    $source->{source}=7;
    need(!eval {validate('guard-test',6,$source);1},'source outside X accepted');
    $choice->{nonce}='PRIVATE';
    need(!eval {validate('guard-test',6,$choice);1},'choice private field accepted');
    print "PASS: four public schemas; rejects private fields, wrong game/seat, nonmember list, wrong recipient/source\n";
    exit;
}
@ARGV==3 or die "usage: perl p6_public_guard_v1.pl EXPECTED_GAME EXPECTED_SEAT PUBLIC_JSON | --self-test\n";
my ($game,$seat,$file)=@ARGV;
open my $f,'<:raw',$file or die "cannot read public JSON\n";
my $text=do {local $/;<$f>}; close $f;
need(length($text)<=1048576,'public input too large');
validate($game,$seat,decode_json($text));
print "PASS: public schema only; authentication and phase history still require review\n";

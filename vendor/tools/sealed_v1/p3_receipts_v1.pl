#!/usr/bin/env perl
use strict;
use warnings;
use JSON::PP;

# PUBLIC inputs only. Seat keys must come from host-published events.
# This checks reports and derives INITIAL ranges under p4's v1 premises.
# It does not decrypt, contact services, publish, vote, or verify private sources.
my $json = JSON::PP->new->canonical(1);
sub seats { my ($m)=@_; return [grep {$m & (1 << ($_-1))} 1..8]; }
sub count { return scalar @{seats($_[0])}; }
sub key { return join(',', @{seats($_[0])}); }
sub small4 { my $s=seats($_[0]); return [@$s[0..3]]; }
sub five {
    my ($v)=@_;
    return undef unless ref($v) eq 'ARRAY' && @$v == 5;
    my ($mask,$last)=(0,0);
    for my $s (@$v) {
        return undef unless defined($s) && !ref($s) && $s =~ /\A[1-8]\z/ && $s > $last;
        $mask |= 1 << ($s-1); $last=$s;
    }
    return $mask;
}
sub scalar_eq {
    return defined($_[0]) && !ref($_[0]) && $_[0] eq $_[1];
}
sub select_plan {
    my ($data)=@_;
    ref($data) eq 'HASH' or die "input object required\n";
    my $game=$data->{game};
    defined($game) && !ref($game) && $game =~ /\A[A-Za-z0-9_-]{1,32}\z/
        or die "valid game required\n";
    ref($data->{receipts}) eq 'HASH' or die "receipts object required\n";
    my (%confirmed,%choice,@ignored);
    for my $s (1..8) {
        $confirmed{$s}={};
        my $r=$data->{receipts}{$s};
        next unless defined $r;
        unless (ref($r) eq 'HASH' && scalar_eq($r->{v},1)
                && scalar_eq($r->{game},$game) && scalar_eq($r->{phase},'receipt')
                && scalar_eq($r->{seat},$s) && ref($r->{lists}) eq 'ARRAY') {
            push @ignored,$s; next;
        }
        for my $l (@{$r->{lists}}) {
            my $m=five($l);
            $confirmed{$s}{$m}=1 if defined($m) && ($m & (1 << ($s-1)));
        }
        my $c=five($r->{four_choice});
        $choice{$s}=$c if defined($c) && ($c & (1 << ($s-1)));
    }
    my %union;
    for my $s (1..8) { $union{$_}=1 for keys %{$confirmed{$s}}; }
    my @kept=map {0+$_} sort {key($a) cmp key($b)} grep {
        my $m=$_;
        !(grep {!$confirmed{$_}{$m}} @{seats($m)});
    } keys %union;
    my $p={game=>$game,retained=>[map {seats($_)} @kept],ignored_reports=>\@ignored,ranges=>[]};
    if (@kept < 1 || @kept > 4) {
        $p->{status}='invalid_premises';
        $p->{reason}='expected one through four retained lists; no guaranteed plan';
        return $p;
    }
    $p->{status}='ready';
    if (@kept <= 3) {
        my @padded=@kept; push @padded,$padded[-1] while @padded < 3;
        $p->{branch}='one_to_three';
        $p->{ranges}=[small4($padded[0]),small4($padded[1]),seats($padded[2])];
        return $p;
    }
    for my $i (0..2) {
        for my $j ($i+1..3) {
            my $intersection=$kept[$i] & $kept[$j];
            next unless count($intersection)==4;
            my @rest=grep {$_ != $kept[$i] && $_ != $kept[$j]} @kept;
            $p->{branch}='four_intersection';
            $p->{selected_pair}=[seats($kept[$i]),seats($kept[$j])];
            $p->{ranges}=[seats($intersection),small4($rest[0]),seats($rest[1])];
            return $p;
        }
    }
    my ($a)=grep {my $bit=1 << ($_-1); (grep {$_ & $bit} @kept)>=3} 1..8;
    defined $a or die "no A: invalid premises\n";
    $p->{A}=$a;
    my $bit=1 << ($a-1);
    if ((grep {$_ & $bit} @kept)==4) {
        unless (defined($choice{$a}) && (grep {$_ == $choice{$a}} @kept)) {
            $p->{status}='missing_honest_choice';
            $p->{reason}="A's valid four_choice required; no substitute inferred";
            return $p;
        }
        $p->{branch}='A_in_four'; $p->{ranges}=[seats($choice{$a})];
        $p->{note}="A's private source calculation remains a protocol premise";
    } else {
        my ($x)=grep {!($_ & $bit)} @kept;
        $p->{branch}='A_in_three'; $p->{X}=seats($x); $p->{ranges}=[small4($x)];
        $p->{note}='on failure STOP: source-report recovery required before a new range';
    }
    return $p;
}
sub task_team {
    my ($p,$q,$failed)=@_;
    $p->{status} eq 'ready' or die "no ready plan\n";
    $q =~ /\A[1-5]\z/ or die "quest must be 1..5\n";
    $failed =~ /\A[0-2]\z/ && $failed < @{$p->{ranges}}
        or die "range exhausted; recovery or new plan required\n";
    my @scope=@{$p->{ranges}[$failed]};
    my $size=(3,4,4,5,5)[$q-1];
    return [@scope[0..$size-1]] if @scope >= $size;
    if ($q==4 && @scope==4) {
        my %in=map {$_=>1} @scope;
        my ($extra)=grep {!$in{$_}} 1..8;
        return [sort {$a<=>$b} (@scope,$extra)];
    }
    die "full five-person range required for quest 5\n";
}
sub test_reports {
    my ($lists,$choices)=@_;
    my %r;
    for my $s (1..8) {
        $r{$s}={v=>1,game=>'test',phase=>'receipt',seat=>$s,
                lists=>[grep {my $l=$_; grep {$_==$s} @$l} @$lists],
                four_choice=>$choices->{$s}//[]};
    }
    return {game=>'test',receipts=>\%r};
}
sub assert { die "self-test failed: $_[1]\n" unless $_[0]; }
sub self_test {
    my $truth=[1,2,3,4,8];
    my $data=test_reports([$truth],{});
    my @all=map {seats($_)} grep {count($_)==5} 0..255;
    $data->{receipts}{5}{lists}=\@all;
    my $p=select_plan($data);
    assert($json->encode($p->{retained}) eq $json->encode([$truth]),'hostile extra lists');
    assert($json->encode(task_team($p,1,0)) eq '[1,2,3]','quest 1');
    assert($json->encode(task_team($p,4,0)) eq '[1,2,3,4,5]','quest 4 supplement');
    assert($json->encode(task_team($p,5,2)) eq '[1,2,3,4,8]','quest 5 full range');
    $data->{receipts}{8}{seat}=1;
    assert(select_plan($data)->{status} eq 'invalid_premises','host seat mismatch');
    $_->{game}='old' for values %{$data->{receipts}};
    assert(select_plan($data)->{status} eq 'invalid_premises','replay');
    assert(!defined(five([1,2,3,4,4])) && !defined(five([1,2,3,4,JSON::PP::true])), 'invalid seats');
    $p=select_plan(test_reports([[1,2,3,4,5],[1,2,3,4,6],[1,4,5,6,7],[2,3,4,6,8]],{}));
    assert($p->{branch} eq 'four_intersection' && $json->encode($p->{ranges}) eq '[[1,2,3,4],[1,4,5,6],[2,3,4,6,8]]','intersection ranges');
    my $four=[[1,2,3,4,5],[1,2,3,6,7],[1,4,5,6,7],[1,2,4,6,8]];
    assert(select_plan(test_reports($four,{}))->{status} eq 'missing_honest_choice','no silent A substitute');
    $p=select_plan(test_reports($four,{1=>[1,2,3,4,5]}));
    assert($p->{branch} eq 'A_in_four' && $p->{A}==1 && @{$p->{ranges}}==1,'A in four');
    $four->[3]=[2,3,4,6,8];
    $p=select_plan(test_reports($four,{}));
    assert($p->{branch} eq 'A_in_three' && $json->encode($p->{ranges}) eq '[[2,3,4,6]]','X range');
    my $ok=eval {task_team($p,2,1);1};
    assert(!$ok,'failed X requires recovery');
    print "PASS: confirmation gate, hostile lists, replay, host seats, four branches, task sizes, recovery stops\n";
}
if (@ARGV==1 && $ARGV[0] eq '--self-test') {self_test();exit;}
@ARGV>=1 && @ARGV<=3 or die "usage: perl p3_receipts_v1.pl INPUT.json [QUEST [FAILED_RANGES]] | --self-test\n";
open my $f,'<:raw',$ARGV[0] or die "cannot read input: $!\n";
my $data=$json->decode(do {local $/;<$f>}); close $f;
my $plan=select_plan($data);
$plan->{team}=task_team($plan,$ARGV[1],$ARGV[2]//0) if @ARGV>=2;
print $json->encode($plan),"\n";

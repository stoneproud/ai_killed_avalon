#!/usr/bin/env perl
use strict;
use warnings;
use JSON::PP;
use Fcntl qw(O_WRONLY O_CREAT O_EXCL);
umask 0077;
my $j=JSON::PP->new->canonical(1);
# Input is PRIVATE: only openings already authenticated and checked by p4_mail.
# This utility neither authenticates inputs nor checks published phase history.
# Output contains the agreed public fields only. No private sources are logged.
sub seat { defined($_[0]) && !ref($_[0]) && $_[0] =~ /\A[1-8]\z/ or die "invalid seat\n"; 0+$_[0] }
sub list {
    my ($v)=@_; ref($v) eq 'ARRAY' && @$v==5 or die "five-seat list required\n";
    my @s=map {seat($_)} @$v; my @sorted=sort {$a<=>$b} @s;
    my %u=map {$_=>1} @s;
    keys(%u)==5 && join(',',@s) eq join(',',@sorted) or die "invalid sorted list\n";
    return \@s;
}
sub key {join(',',@{$_[0]})}
sub has {my ($l,$s)=@_; scalar grep {$_==$s} @$l}
sub overlap {my ($a,$b)=@_; scalar grep {has($b,$_)} @$a}
sub no_four_intersection {
    my ($lists)=@_;
    for my $i (0..$#$lists-1) {for my $k ($i+1..$#$lists) {
        return 0 if overlap($lists->[$i],$lists->[$k])>=4;
    }}
    return 1;
}
sub choose {
    my ($lists,$sources)=@_; return [] unless @$lists==4 && keys(%$sources)==4;
    my @c=grep {my $l=$_; (grep {has($l,$_)} keys %$sources)==1} @$lists;
    return @c==1 ? $c[0] : [];
}
sub build {
    my ($mode,$d)=@_;
    ref($d) eq 'HASH' && defined($d->{v}) && $d->{v}==1 or die "private input v1 required\n";
    my $g=$d->{game}; defined($g) && !ref($g) && $g =~ /\A[A-Za-z0-9_-]{1,32}\z/ or die "invalid game\n";
    my $s=seat($d->{seat}); ref($d->{verified}) eq 'ARRAY' or die "verified records required\n";
    my (%lists,%by_source);
    for my $r (@{$d->{verified}}) {
        ref($r) eq 'HASH' or die "invalid record\n";
        my $l=list($r->{list}); my $f=seat($r->{source}); my $k=key($l);
        has($l,$s) && has($l,$f) or die "recipient or source absent\n";
        !exists($by_source{$f}) || $by_source{$f} eq $k or die "one source opened distinct lists\n";
        $by_source{$f}=$k; $lists{$k}=$l;
    }
    my @l=map {$lists{$_}} sort keys %lists;
    @l<=4 or die "more than four verified lists violates premises\n";
    if ($mode eq 'receipt') {
        my $c=(@l==4 && no_four_intersection(\@l)) ? choose(\@l,\%by_source) : [];
        return {v=>1,game=>$g,phase=>'receipt',seat=>$s,lists=>\@l,four_choice=>$c};
    }
    $mode eq 'recovery' or die "unknown mode\n";
    ref($d->{recovery}) eq 'HASH' or die "recovery context required\n";
    my $x=list($d->{recovery}{X}); my $f=seat($d->{recovery}{excluded_source});
    @l==3 && !has($x,$s) && has($x,$f) && !exists($lists{key($x)})
        or die "invalid A/X context\n";
    !exists($by_source{$f}) or die "excluded source already bound elsewhere\n";
    $by_source{$f}=key($x); push @l,$x;
    no_four_intersection(\@l) or die "not the no-intersection branch\n";
    my ($a)=grep {my $p=$_; (grep {has($_,$p)} @l)>=3} 1..8;
    defined($a) && $a==$s or die "caller is not A\n";
    my $c=choose(\@l,\%by_source);
    @$c==5 && key($c) ne key($x) or die "no unique remaining choice\n";
    return {v=>1,game=>$g,phase=>'x_choice',seat=>$s,X=>$x,excluded_source=>$f,choice=>$c};
}
sub assert {$_[0] or die "self-test failed: $_[1]\n"}
sub selftest {
    my $base=[[1,2,3,4,5],[1,2,3,6,7],[1,4,5,6,7],[1,2,4,6,8]];
    my ($receipt,$recovery);
    for my $m (1..5) {
        my @f=($m,6,7,8);
        my $d={v=>1,game=>'selftest',seat=>1,verified=>[map {{list=>$base->[$_],source=>$f[$_]}} 0..3]};
        my $r=build('receipt',$d);
        assert(key($r->{four_choice}) eq '1,2,3,4,5','four choice');
        my $bytes=$j->encode($r); $receipt //= $bytes;
        assert($bytes eq $receipt,'public receipt independent of Merlin position');
        pop @{$d->{verified}};
        $d->{recovery}={X=>[2,3,4,6,8],excluded_source=>8};
        $r=build('recovery',$d);
        assert(key($r->{choice}) eq '1,2,3,4,5','recovery choice');
        $bytes=$j->encode($r); $recovery //= $bytes;
        assert($bytes eq $recovery,'public recovery independent of Merlin position');
    }
    my $d={v=>1,game=>'selftest',seat=>1,verified=>[]};
    assert(@{build('receipt',$d)->{lists}}==0,'empty receipt');
    $d->{verified}=[{list=>$base->[0],source=>1},{list=>$base->[0],source=>1}];
    assert(@{build('receipt',$d)->{lists}}==1,'deduplication');
    push @{$d->{verified}},{list=>$base->[1],source=>1};
    assert(!eval {build('receipt',$d);1},'source binding');
    $d->{verified}=[{list=>$base->[0],source=>8}];
    assert(!eval {build('receipt',$d);1},'source membership');
    print "PASS: receipt/recovery choices, five Merlin permutations, deduplication, source binding\n";
}
if (@ARGV==1 && $ARGV[0] eq '--self-test') {selftest();exit}
@ARGV==3 or die "usage: perl p1_selection_v1.pl receipt|recovery PRIVATE_INPUT NEW_PUBLIC_OUTPUT | --self-test\n";
my ($mode,$in,$out)=@ARGV;
open my $f,'<:raw',$in or die "cannot read private input\n";
my $d=$j->decode(do {local $/;<$f>}); close $f;
my $r=build($mode,$d);
sysopen my $o,$out,O_WRONLY|O_CREAT|O_EXCL,0600 or die "output must be a new file\n";
print {$o} $j->encode($r),"\n" or die "write failed\n";
close $o or die "close failed\n";
print "public report created\n";

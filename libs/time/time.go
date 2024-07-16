package time

import (
	"math/rand"
	"time"
)

// Now returns the current time in UTC with no monotonic component.
func Now() time.Time {
	return Canonical(time.Now())
}

// Canonical returns UTC time with no monotonic component.
// Stripping the monotonic component is for time equality.
// See https://github.com/tendermint/tendermint/pull/2203#discussion_r215064334
func Canonical(t time.Time) time.Time {
	return t.Round(0).UTC()
}

func OnlyDelay(dur time.Duration) (int64, int64) {
	time.Sleep(dur)
	return 0, 0
}

// [log by yiiguo] 基于负指数分布的时间延迟
func FuDelay(dur time.Duration) (int64, int64) {
	if dur == 0 {
		return 0, 0
	}
	const INTERVAL = 10 * time.Millisecond // [log by yiiguo] 每 10 ms 检查一次
	const MAXVAL = 10000
	cnt := dur / INTERVAL // [log by yiiguo] dur 是总时间, 基于毫秒的, cnt 就是要检查的次数
	limit := MAXVAL / cnt // [log by yiiguo] 当随机值小于 limit 的时候, 退出
	rand.Seed(time.Now().UnixNano())
	len := cnt * 3
	//fmt.Printf("cnt:%d", cnt)
	for i := 0; i < int(len); i++ {
		// i := 0
		// for i{
		randval := rand.Intn(MAXVAL)
		if randval < int(limit) {
			return int64(i + 1), int64(randval)
		}
		// i += 1
		time.Sleep(INTERVAL) // [log by yiiguo] 每隔 INTERVAL 毫秒就检查一次
	}
	return int64(len), 0
}

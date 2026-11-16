package server

import (
	"errors"
	"io"
	"net"
	"strings"
	"sync"
)

type Connection struct {
	conn     net.Conn
	readBuf  strings.Builder
	readMu   sync.Mutex
	writeMu  sync.Mutex
	isClosed bool
}

func NewConnection(conn net.Conn) *Connection {
	return &Connection{
		conn: conn,
	}
}

func (c *Connection) RemoteAddr() string {
	if c.conn == nil {
		return "unknown"
	}
	return c.conn.RemoteAddr().String()
}

func (c *Connection) WriteLine(msg string) error {
	c.writeMu.Lock()
	defer c.writeMu.Unlock()

	if c.isClosed {
		return io.ErrClosedPipe
	}

	if !strings.HasSuffix(msg, "\n") {
		msg += "\n"
	}

	data := []byte(msg)
	totalSent := 0

	// Loop until all bytes are sent
	for totalSent < len(data) {
		n, err := c.conn.Write(data[totalSent:])
		if err != nil {
			return err
		}
		totalSent += n
	}

	return nil
}

func (c *Connection) Close() error {
	if c.isClosed {
		return errors.New("Error: Connection already closed")
	}
	c.isClosed = true
	return c.conn.Close()
}

func (c *Connection) ReadLine() (string, error) {
	c.readMu.Lock()
	defer c.readMu.Unlock()

	if c.isClosed {
		return "", io.EOF
	}

	buf := make([]byte, 4096)

	for {
		current := c.readBuf.String()

		// 1. check if we have complete line in buffer
		if idx := strings.IndexByte(current, '\n'); idx >= 0 {
			line := current[:idx]
			remainder := current[idx+1:]

			c.readBuf.Reset()
			c.readBuf.WriteString(remainder)

			return strings.TrimRight(line, "\r"), nil
		}

		// 2. buffer doesn't have full line
		n, err := c.conn.Read(buf)
		if n > 0 {
			c.readBuf.Write(buf[:n])
		}

		// 3. handle disconnection or socket error
		if err != nil {
			// if client disconnected but left some text without newline
			remaining := c.readBuf.String()
			c.readBuf.Reset()
			if len(strings.TrimSpace(remaining)) > 0 {
				return strings.TrimRight(remaining, "\r"), nil
			}
			return "", err
		}
	}

}

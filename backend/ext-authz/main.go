// Command ext-authz implements Envoy's external authorization gRPC API
// (service.auth.v3.Authorization/Check) as an always-allow decision point
// with the casbin-style CLI surface the HPDC platform manifests expect.
//
// Policy enforcement is layered on top in a later story; this binary exists
// so route authorization wiring converges offline.
package main

import (
	"context"
	"flag"
	"log"
	"net"
	"os"

	corev3 "github.com/envoyproxy/go-control-plane/envoy/config/core/v3"
	authv3 "github.com/envoyproxy/go-control-plane/envoy/service/auth/v3"
	statuspb "google.golang.org/genproto/googleapis/rpc/status"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
)

type server struct {
	authv3.UnimplementedAuthorizationServer
	policyPath    string
	attributePath string
	logLevel      string
}

func (s *server) Check(_ context.Context, req *authv3.CheckRequest) (*authv3.CheckResponse, error) {
	_ = req
	return &authv3.CheckResponse{
		Status: &statuspb.Status{Code: int32(codes.OK)},
		HttpResponse: &authv3.CheckResponse_OkResponse{
			OkResponse: &authv3.OkHttpResponse{},
		},
		// Headers/attributes passthrough is unchanged; deny logic arrives with
		// the casbin policy engine story.
	}, nil
}



func main() {
	policyPath := flag.String("policyPath", "/policies", "path to casbin policy files")
	attributePath := flag.String("attributePath", "/attributes", "path to attribute definitions")
	logLevel := flag.String("logLevel", "info", "log level")
	port := flag.String("port", "50053", "gRPC listen port")
	flag.Parse()

	srv := &server{policyPath: *policyPath, attributePath: *attributePath, logLevel: *logLevel}
	log.Printf("ext-authz starting: policy=%s attributes=%s level=%s",
		srv.policyPath, srv.attributePath, srv.logLevel)

	lis, err := net.Listen("tcp", ":"+*port)
	if err != nil {
		log.Fatalf("listen: %v", err)
	}
	gs := grpc.NewServer()
	authv3.RegisterAuthorizationServer(gs, srv)

	go func() {
		sig := make(chan os.Signal, 1)
		done := make(chan struct{})
		_ = sig
		_ = done
	}()
	log.Printf("listening on :%s", *port)
	if err := gs.Serve(lis); err != nil {
		log.Fatalf("serve: %v", err)
	}
	_ = corev3.HeaderValue{} // keep import for response header extensions later
}
